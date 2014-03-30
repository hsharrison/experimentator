"""Design objects.

This module contains objects related to experimental design abstractions. This module is not public; its public objects
are imported in ``__init__.py``.

"""
import itertools
import collections
from copy import copy
import numpy as np

import experimentator.order
from collections import ChainMap


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
    extra_data : dict, optional
        Dictionary elements that will be included in the data of `ExperimentSection` instances created under this
        `Design`.

    """
    def __init__(self, ivs=None, design_matrix=None, ordering=None, extra_data=None):
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
        self.extra_data = extra_data or {}

        if ordering:
            self.ordering = ordering
        else:
            self.ordering = experimentator.order.Ordering()

        if self.design_matrix is None and any(iv_values is None for iv_values in self.iv_values):
            raise TypeError('Must specify a design matrix if using continuous IVs (values=None)')

    @classmethod
    def from_dict(cls, spec):
        """
        Design from dict.

        Constructs a `Design` instance from a dict (e.g., parsed from a YAML file).

        Arguments
        ---------
        spec : dict
            The fields 'ivs'`, `'design_matrix'`, and `'extra_data'` are interpreted as
            kwargs to the `Design` constructor.
            An `Ordering` instance is created from the field `'ordering'` or `'order'`.
            This field may contain a string, dict, or sequence.
            A string is interpreted as a class name from `experimentator.order`.
            If the ordering spec is a dict, then the field `'class'` contains the class name
            and other fields are interpreted as keyword arguments to the constructor.
            If the ordering spec is a sequence, then the first element is the class name
            and any subsequent elements are positional arguments.
            F or convenience, the `Ordering` argument `number` may be specified in `spec['n']` or `spec['number']`.
            Finally, any fields not otherwise used
            are included in the `extra_data` argument to the `Design` constructor.

        Returns
        -------
        name : str
            Only returned if `spec` contains a field `'name'`.
        design : Design

        """
        inputs = spec.copy()

        ordering_spec = inputs.pop('ordering', inputs.pop('order', None))
        ordering_class = 'Ordering'
        ordering_args = ()
        number = inputs.pop('number', inputs.pop('n', None))
        ordering_kwargs = {'number': number} if number else {}

        name = inputs.pop('name', None)
        design_kwargs = {key: inputs.get(key)
                         for key in inputs
                         if key in ('ivs', 'design_matrix', 'extra_data')}
        inputs.pop('ivs', None)
        inputs.pop('design_matrix', None)
        inputs.pop('extra_data', None)
        design_kwargs['extra_data'] = inputs

        if isinstance(ordering_spec, str):
            ordering_class = ordering_spec

        elif isinstance(ordering_spec, dict):
            ordering_class = ordering_spec.pop('class', ordering_class)
            ordering_kwargs.update(ordering_spec)

        elif isinstance(ordering_spec, collections.Sequence):
            ordering_class = ordering_spec[0]
            ordering_args = ordering_spec[1:]

        ordering = getattr(experimentator.order, ordering_class)(*ordering_args, **ordering_kwargs)

        self = cls(ordering=ordering, **design_kwargs)
        if name:
            return name, self
        else:
            return self

    def __repr__(self):
        return 'Design(ivs={}, design_matrix={}, ordering={}, extra_data={})'.format(
            list(zip(self.iv_names, self.iv_values)), self.design_matrix, self.ordering, self.extra_data)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__ == other.__dict__

    def get_order(self, data=None):
        order = self.ordering.get_order(data)
        for condition in order:
            condition.update(self.extra_data)
        return order

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
            print(np.shape(self.design_matrix))
            print(self.iv_names)
            if not np.shape(self.design_matrix)[1] == len(self.iv_names):
                raise TypeError("Size of design matrix doesn't match number of IVs")

            all_conditions = self._parse_design_matrix(self.design_matrix)

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
        values_per_factor = [np.unique(column) for column in np.transpose(design_matrix)]
        if any(iv_values and not len(iv_values) == len(values)
               for iv_values, values in zip(self.iv_values, values_per_factor)):
            raise ValueError('Unique elements in design matrix do not match number of values in IV definition')

        conditions = []
        for row in design_matrix:
            condition = self.extra_data.copy()
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

    def __repr__(self):
        if self.levels_and_designs[0][0] == '_base':
            levels_and_designs = self.levels_and_designs[1:]
        else:
            levels_and_designs = self.levels_and_designs
        return 'DesignTree({})'.format(levels_and_designs)

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

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__ == other.__dict__

    def add_base_level(self):
        """Add base level to tree.

        Adds a section to the top of the tree called ``'_base'``. This makes the `DesignTree` suitable for constructing
        an `Experiment`.

        Note
        ----
        The `Experiment` constructor calls this automatically, and this shouldn't be called when appending a tree to an
        existing `Experiment`, so there are no real reasons to call this in client code.

        """
        levels_and_designs = [('_base', Design())]
        levels_and_designs.extend(self.levels_and_designs)
        self.levels_and_designs = levels_and_designs
