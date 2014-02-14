"""Design objects.

This module contains objects related to experimental design abstractions. This module is not public; its public objects
are imported in ``__init__.py``.

"""
import itertools
from copy import copy
import numpy as np

from experimentator.order import Shuffle


class Design():
    """Experimental design object.

    An instance of this class organizes the experimental design at one level of the experimental hierarchy. It directs
    the creation of `ExperimentSection` objects by parsing design matrices or crossing independent variables.

    Arguments
    ---------
    ivs : dict or list of tuple, optional
        List of tuples describing independent variables (IVs). Each  tuple is of length 2, with the first element being
        a string naming the IV, and the second a sequence containing the possible values of that IV. Alternatively, the
        second element can be None, which represents an IV that takes continuous values. In that case, the values for
        that IV are taken from `design_matrix`. If `ivs` is omitted or empty, a `Design` with no IVs will be created.
        IVs can also be passed as a dictionary, with keys as IV names and values as possible IV values. While this
        format is more convenient, order is not guaranteed for a dictionary so it does not work well with design
        matrices. However, using an `OrderedDict` is a possible solution.
    design_matrix : array-like, optional
        An experimental design matrix specifying how IV values should be grouped to form conditions. Each column
        represents one IV, and each row represents one condition. Values in `design_matrix` do not have to conform to
        IV values as passed in `ivs`; rather, the unique elements of each column are each associated with one value from
        `ivs`. Design matrices produced by :mod:`pyDOE` are compatible as-is. If no `design_matrix` is given, the IV
        values will be fully crossed.
    ordering : Ordering instance, optional
        An instance of an `experimentator.order.Ordering` subclass, defining the behavior for duplicating and ordering
        the conditions of the `Design`. If no `ordering` is given, the default is `experimentator.order.Shuffle()`.
    **extra_context
        Arbitrary keyword arguments that will be included in the context of `ExperimentSection` instances created under
        this `Design`. For example, if the keyword argument `practice=True`, any `ExperimentSection` objects resulting
        from this `Design` will have `{'practice': True}` as an element of their `context` attribute.

    """
    def __init__(self, ivs=None, design_matrix=None, ordering=None, **extra_context):
        if isinstance(ivs, dict):
            ivs = list(ivs.items())
        if ivs:
            iv_names, iv_values = zip(*ivs)
            self.iv_names = list(iv_names)
            self.iv_values = list(iv_values)
        else:
            self.iv_names = []
            self.iv_values = []

        self.design_matrix = design_matrix
        self.extra_context = extra_context

        if ordering:
            self.ordering = ordering
        else:
            self.ordering = Shuffle()

        if self.design_matrix is None and any(iv_values is None for iv_values in self.iv_values):
            raise TypeError('Must specify a design matrix if using continuous IVs (values=None)')

        self.get_order = self.ordering.get_order

    def first_pass(self):
        """First pass of design.

        Initialize the design by parsing the design matrix or otherwise crossing the IVs. If a non-atomic ordering is
        used, an additional IV will be returned which should be incorporated into the design one level up in the
        experimental hierarchy. For this reason, the `first_pass` methods in a hierarchy of `Design` instances should be
        called in reverse order, from bottom up. The `DesignTree` class handles this.

        Returns
        -------
        new_iv : list
           If `Design.ordering` is non-atomic, a list will be returned, giving the values of a new IV to be created one
           level up in the experimental hierarchy. Typically, each value corresponds to a unique ordering of the
           conditions in this `Design`. If `Design.ordering` is non-atomic,

        """
        if self.design_matrix is not None:
            all_conditions = self._parse_design_matrix(self.design_matrix)
            for condition in all_conditions:
                condition.update(self.extra_context)

        else:
            all_conditions = self.full_cross(self.iv_names, self.iv_values)

        return self.ordering.first_pass(all_conditions)

    def update(self, names, values):
        """Add new IVs to design.

        This method adds new IVs to the `Design`. It will have no effect after `Design.first_pass` has been called.

        Arguments
        ---------
        names : list of str
            Names of IVs to add.
        values : list of list
            For each IV, a list of possible values.

        """
        self.iv_names.extend(names)
        self.iv_values.extend(values)

    @staticmethod
    def full_cross(iv_names, iv_values):
        """Full factorial cross of IVs.

        Arguments
        ---------
        iv_names : list of str
            Names of IVs.
        iv_values : list of list
            Each element defines the possible values of an IV. Must be the same length as `iv_names`. Note that IV
            values must be hashable (not the list of values of course, but each element of the list).

        Yields
        ------
        condition : dict
            A dictionary describing one condition, with keys of IV names and values of specific values of the IV. One
            dictionary is yielded for every possible combination of IV values.

        """
        iv_combinations = itertools.product(*iv_values)

        yield from (dict(zip(iv_names, iv_combination)) for iv_combination in iv_combinations)

    def _parse_design_matrix(self, design_matrix):
        if not np.shape(design_matrix)[1] == len(self.iv_names):
            raise ValueError('Number of columns in design matrix not equal to number of IVs')

        values_per_factor = [np.unique(column) for column in np.transpose(design_matrix)]
        if any(iv_values and not len(iv_values) == len(values)
               for iv_values, values in zip(self.iv_values, values_per_factor)):
            raise ValueError('Unique elements in design matrix do not match number of values in IV definition')

        conditions = []
        for row in design_matrix:
            condition = self.extra_context.copy()
            for iv_name, iv_values, factor_values, design_matrix_value in \
                    zip(self.iv_names, self.iv_values, values_per_factor, row):
                if iv_values:
                    condition.update({iv_name: np.array(iv_values)[factor_values == design_matrix_value][0]})
                else:
                    condition.update({iv_name: design_matrix_value})
            conditions.append(condition)

        return conditions


class DesignTree():
    """Hierarchy of experimental designs.

    A container for `Design` instances, describing the entire hierarchy of a basic `Experiment`. `DesignTree` instances
    are iterators; calling `next` on a `DesignTree` will return a `DesignTree` with the top level removed. In this way,
    the entire experimental hierarchy can be created by recursively calling `DesignTree.__next__`.

    Arguments
    ---------
    levels_and_design : list of tuple
       A list of tuples, each with two elements. The first is a string naming the level, the second is a list of
       `Design` instances to occur at that level.

    Note
    ----
    This class does not have much functionality. Its only purpose is to handle calling `Design.first_pass` for every
    `Design` object, in the proper order. This streamlines customizing an experiment with different designs in different
    places, and prevents errors such as calling `Design.first_pass` methods multiple times or in the wrong order.

    """
    def __init__(self, levels_and_designs):
        # Make first pass of all designs, from bottom to top.
        for (level, designs), (level_above, designs_above) in \
                zip(reversed(levels_and_designs[1:]), reversed(levels_and_designs[:-1])):

            # Call first_pass and add new IVs.
            new_iv_names = []
            new_iv_values = []
            for design in designs:
                iv_name, iv_values = design.first_pass()
                if iv_name:
                    new_iv_names.append(iv_name)
                    new_iv_values.append(iv_values)
            for design in designs_above:
                design.update(new_iv_names, new_iv_values)

        # And call first pass of the top level.
        for design in levels_and_designs[0][1]:
            design.first_pass()

        self.levels_and_designs = levels_and_designs

    def __next__(self):
        if len(self.levels_and_designs) == 1:
            raise StopIteration
        next_design = copy(self)
        next_design.levels_and_designs = next_design.levels_and_designs[1:]
        return next_design

    def __len__(self):
        return len(self.levels_and_designs)

    def __getitem__(self, item):
        return self.levels_and_designs[item]

    def add_base_level(self):
        """Add base level to tree.

        Adds a section to the top of the tree called ``'base'``. This makes the `DesignTree` suitable for constructing
        an `Experiment`.

        Note
        ----
        The `Experiment` constructor calls this automatically, and this shouldn't be called when appending a tree to an
        existing `Experiment`, so there are no real reasons to call this in client code.

        """
        levels_and_designs = [('base', Design())]
        levels_and_designs.extend(self.levels_and_designs)
        self.levels_and_designs = levels_and_designs
