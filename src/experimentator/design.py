"""
This module contains objects related to experimental design abstractions.
Public objects are imported in ``__init__.py``.

"""
from collections.abc import Iterable
import itertools
import collections
from copy import copy
import numpy as np
from schema import Schema, Or, Optional, And, Use

import experimentator.order as order

Level = collections.namedtuple('Level', ('name', 'design'))


class Design:
    """
    |Design| instances specify the experimental design at one level of the experimental hierarchy.
    They guide the creation of |ExperimentSection| instances
    by parsing design matrices or crossing independent variables (IVs).

    Parameters
    ----------
    ivs : dict or list of tuple, optional
        Independent variables can be specified as a dictionary mapping names to possible values,
        or as a list of ``(name, values)`` tuples.
        If an IV takes continuous values, use ``None`` for its levels.
        This only works when specifying values using `design_matrix`.
        See the |IV docs| for more information.
    design_matrix : array-like, optional
        A |numpy array| (or convertible, e.g. a list-of-lists)
        representing a design matrix specifying how IV values should be grouped to form conditions.
        When no `design_matrix` is passed, IVs are fully crossed.
        See the |design matrix docs| for more details.
        Note that a design matrix may also specify the order of the conditions.
        For this reason, the default `ordering` changes from |Shuffle| to |Ordering|,
        preserving the order of the conditions.
    ordering : |Ordering|, optional
        An instance of |Ordering| or one of its subclasses defining the behavior
        for duplicating and ordering the conditions of the |Design|.
        The default is |Shuffle| unless a `design_matrix` is passed.
    extra_data : dict, optional
        Items from this dictionary will be included in the |data| attribute
        of any |ExperimentSection| instances created with this |Design|.

    Attributes
    ----------
    iv_names : list of str
    iv_values : list of tuple
    design_matrix : array-like
    extra_data : dict
    ordering : |Ordering|
    heterogeneous_design_iv_name : str
        The IV name that triggers a heterogeneous (i.e., branching) tree structure when it is encountered.
        ``'design'`` by default.
    is_heterogeneous : bool
        True if this |Design| is the lowest level before the tree structure diverges.
    branches : dict
        The IV values corresponding to named heterogeneous branches in the tree structure following this |Design|.

    See Also
    --------
    experimentator.order
    experimentator.DesignTree

    Examples
    --------
    >>> from experimentator.order import Shuffle
    >>> design = Design(ivs={'side': ['left', 'right'], 'difficulty': ['easy', 'hard']}, ordering=Shuffle(2))
    >>> design.first_pass()
    IndependentVariable(name=(), values=())
    >>> design.get_order()
    [{'difficulty': 'easy', 'side': 'left'},
     {'difficulty': 'hard', 'side': 'left'},
     {'difficulty': 'easy', 'side': 'left'},
     {'difficulty': 'hard', 'side': 'right'},
     {'difficulty': 'easy', 'side': 'right'},
     {'difficulty': 'easy', 'side': 'right'},
     {'difficulty': 'hard', 'side': 'left'},
     {'difficulty': 'hard', 'side': 'right'}]

    """
    heterogeneous_design_iv_name = 'design'

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
        elif design_matrix is None:
            self.ordering = order.Shuffle()
        else:
            self.ordering = order.Ordering()

        if self.design_matrix is None and any(iv_values is None for iv_values in self.iv_values):
            raise TypeError('Must specify a design matrix if using continuous IVs (values=None)')

    @classmethod
    def from_dict(cls, spec):
        """Construct a |Design| instance from a specification based on dictionaries (e.g., parsed from a YAML file).

        Parameters
        ----------
        spec : dict
            A dictionary containing some of the following keys (all optional):
            ``'name'``, the name of the level;
            ``'ivs'``, ``'design_matrix'``, ``'extra_data'``, keyword arguments to the |Design| constructor;
            ``'order'`` or ``'ordering'``, a string, dictionary, or list determining the ordering method; and
            ``'n'`` or ``'number'``, the ``number`` argument to the specified ordering.
            A dictionary containing any fields not otherwise used
            is passed to the |Design| constructor as the ``extra_data`` argument.
            See the |description in the docs| for more information.

        Returns
        -------
        name : str
            Only returned if `spec` contains a field ``'name'``.
        design : |Design|

        See Also
        --------
        experimentator.DesignTree.from_spec

        Examples
        --------
        >>> design_spec = {
        ...'name': 'block',
        ...'ivs': {'speed': [1, 2, 3], 'size': [15, 30]},
        ...'ordering': 'Shuffle',
        ...'n': 3}
        >>> Design.from_dict(design_spec)
        Level(name='block', design=Design(ivs=[('speed', [1, 2, 3]), ('size', [15, 30])], design_matrix=None, ordering=Shuffle(number=3, avoid_repeats=False), extra_data={}))

        """
        inputs = Schema({
            Optional('name'): And(str, len),
            Optional('ivs'): And(Use(dict), {Optional(And(str, len)): Iterable}),
            Optional('design_matrix'): Use(np.asarray),
            Optional(Or('order', 'ordering')): Use(order.OrderSchema.from_any),
            Optional(Or('n', 'number')): int,
            Optional(
                lambda x: x not in {'name', 'ivs', 'design_matrix', 'order', 'ordering', 'n', 'number'}
                # Necessary due to https://github.com/keleshev/schema/issues/57
            ): object,
        }).validate(spec)
        if 'n' in inputs:
            inputs['number'] = inputs.pop('n')
        if 'order' in inputs:
            inputs['ordering'] = inputs.pop('order')

        if 'ordering' not in inputs:
            inputs['ordering'] = order.Ordering() if 'design_matrix' in inputs else order.Shuffle()

        if 'number' in inputs:
            inputs['ordering'].number = inputs.pop('number')

        name = inputs.pop('name', None)

        extra_keys = set(inputs) - {'ivs', 'design_matrix', 'ordering'}
        if extra_keys:
            inputs['extra_data'] = {key: inputs.pop(key) for key in extra_keys}

        self = cls(**inputs)
        return Level(name, self) if name else self

    def __repr__(self):
        return 'Design(ivs={}, design_matrix={}, ordering={}, extra_data={})'.format(
            list(zip(self.iv_names, self.iv_values)), self.design_matrix, self.ordering, self.extra_data)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__ == other.__dict__
        return False

    def get_order(self, data=None):
        """Order the conditions.

        Returns
        -------
        list of dict
            A list of dictionaries, each specifying a condition (a mapping from IV names to values).

        """
        condition_order = self.ordering.get_order(data)
        for condition in condition_order:
            condition.update(self.extra_data)
        return condition_order

    def first_pass(self):
        """Initialize design.

        Initializes the design by parsing the design matrix or crossing the IVs
        If a |NonAtomicOrdering| is used, an additional IV will be returned
        which should be incorporated into the design one level up in the experimental hierarchy.
        For this reason, the |first_pass| methods in a hierarchy of |Design| instances
        should be called in reverse order, from bottom up.
        Use a |DesignTree| to ensure this occurs properly.

        Returns
        -------
        iv_name : str or tuple
            The name of the IV, for |non-atomic orderings|.
            Otherwise, an empty tuple.
        iv_values : tuple
            The possible values of the IV.
            Empty for atomic orderings.

        """
        if self.design_matrix is not None:
            if not np.shape(self.design_matrix)[1] == len(self.iv_names):
                raise TypeError("Size of design matrix doesn't match number of IVs")

            all_conditions = self._parse_design_matrix(self.design_matrix)

        else:
            all_conditions = self.full_cross(self.iv_names, self.iv_values)

        return self.ordering.first_pass(all_conditions)

    def update(self, names, values):
        """
        Add additional independent variables to the |Design|.
        This will have no effect after |Design.first_pass| has been called.

        Parameters
        ----------
        names : list of str
            Names of IVs to add.
        values : list of list
            For each IV, a list of possible values.

        """
        self.iv_names.extend(names)
        self.iv_values.extend(values)

    @staticmethod
    def full_cross(iv_names, iv_values):
        """
        Perform a full factorial cross of the independent variables.
        Yields dictionaries, each describing one condition, a mapping from IV names to IV values.
        One dictionary is yielded for every possible combination of IV values.

        Parameters
        ----------
        iv_names : list of str
            Names of IVs.
        iv_values : list of list
            Each element defines the possible values of an IV.
            Must be the same length as `iv_names`.
            Its elements must be hashable.

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
            for iv_name, iv_values, factor_values, design_matrix_value in zip(
                    self.iv_names, self.iv_values, values_per_factor, row):
                if iv_values:
                    condition.update({iv_name: np.array(iv_values)[factor_values == design_matrix_value][0]})
                else:
                    condition.update({iv_name: design_matrix_value})
            conditions.append(condition)

        return conditions

    @property
    def is_heterogeneous(self):
        return self.heterogeneous_design_iv_name in self.iv_names

    @property
    def branches(self):
        return dict(zip(self.iv_names, self.iv_values)).get(self.heterogeneous_design_iv_name, ())


class DesignTree:
    """
    A container for |Design| instances, describing the entire hierarchy of a basic |Experiment|.
    |DesignTree| instances are iterators; calling ``next`` on one
    will return another |DesignTree| with the top level removed.
    In this way, the entire experimental hierarchy can be created by recursively calling ``next``.

    Use |DesignTree.new| to create a new tree, the generic constructor is for instantiating trees
    whose attributes have already been processed (i.e., reloading already-created trees).

    Attributes
    ----------
    levels_and_designs : list of tuple
    other_designs : dict
    branches : dict
        Only those items from `other_designs` that follow directly from this tree.

    Notes
    -----
    Calling ``next`` on the last level of a heterogeneous |DesignTree|
    will return a dictionary of named |DesignTree| instances
    (rather than a single |DesignTree| instance).
    The keys are the possible values of the IV ``'design'``
    and the values are the corresponding |DesignTree| instances.

    """
    def __init__(self, levels_and_designs=None, other_designs=None, branches=None):
        self.levels_and_designs = levels_and_designs or []
        self.other_designs = other_designs or {}
        self.branches = branches or {}

    @classmethod
    def new(cls, levels_and_designs, **other_designs):
        """Create a new |DesignTree|.

        Parameters
        ----------
        levels_and_designs : |OrderedDict| or list of tuple
            This input defines the structure of the tree, and is either an |OrderedDict| or a list of 2-tuples.
            Keys (or first element of each tuple) are level names.
            Values (or second element of each tuple) are design specifications,
            in the form of either a |Design| instance, or a list of |Design| instances to occur in sequence.

        **other_designs
            Named design trees, can be other |DesignTree| instances or suitable `levels_and_designs` inputs
            (i.e., |OrderedDict| or list of tuples).
            These designs allow for heterogeneous design structures
            (i.e. not every section at the same level has the same |Design|).
            To make a heterogeneous |DesignTree|,
            use an IV named ``'design'`` at the level where the heterogeneity should occur.
            Values of this IV should be strings,
            each corresponding to the name of a |DesignTree| from` other_designs`.
            The value of the IV ``'design'`` at each section
            determines which |DesignTree| is used for children of that section.

        """
        if isinstance(levels_and_designs, collections.OrderedDict):
            levels_and_designs = list(levels_and_designs.items())

        # Check for singleton Designs.
        for i, (level, design) in enumerate(levels_and_designs):
            if isinstance(design, Design):
                levels_and_designs[i] = (level, [design])

        # Convert to namedtuples.
        levels_and_designs = [Level(*level) for level in levels_and_designs]

        # Handle heterogeneous trees.
        bottom_level_design = levels_and_designs[-1].design[0]
        if bottom_level_design.is_heterogeneous:
            branches = {name: branch for name, branch in other_designs.items()
                        if branch in bottom_level_design.branches and isinstance(branch, DesignTree)}
            for branch_name in bottom_level_design.branches:
                if branch_name not in branches:
                    designs_to_pass = other_designs.copy()
                    del designs_to_pass[branch_name]
                    tree = DesignTree.new(other_designs[branch_name], **designs_to_pass)
                    branches[branch_name] = tree

        else:
            branches = {}

        self = cls(levels_and_designs, other_designs, branches)
        self.first_pass(self.levels_and_designs)
        return self

    @classmethod
    def from_spec(cls, spec):
        """
        Constructs a |DesignTree| instance from a specification (e.g., parsed from a YAML file).

        spec : dict or list of dict
            The |DesignTree| specification.
            A dictionary with keys as tree names and values as lists of dictionaries.
            Each sub-dictionary should specify a |Design| according to |Design.from_dict|.
            The main tree should be named ``'main'``.
            Other names are used for generating heterogeneous trees
            (see |DesignTree| docs).
            A homogeneous tree can be specified as a dictionary with only a single key ``'main'``,
            or directly as a list of dictionaries

        Returns
        -------
        |DesignTree|

        """
        if isinstance(spec, dict):
            # The normal case.
            main_tree = list(cls._design_specs_to_designs(spec.pop('main')))
            other_trees = {name: list(cls._design_specs_to_designs(specs)) for name, specs in spec.items()}
        else:
            # Only a main design.
            main_tree = list(cls._design_specs_to_designs(spec))
            other_trees = {}

        return cls.new(main_tree, **other_trees)

    @staticmethod
    def _design_specs_to_designs(specs):
        for spec in specs:
            if isinstance(spec, dict):
                name_and_design = Design.from_dict(spec)
                if isinstance(name_and_design, Design):
                    yield None, name_and_design
                else:
                    yield name_and_design

            else:
                name = None
                designs = []
                for design_spec in spec:
                    name_and_design = Design.from_dict(design_spec)
                    if isinstance(name_and_design, Design):
                        designs.append(name_and_design)
                    else:
                        if name and name_and_design[0] != name:
                            raise ValueError('Designs at the same level must have the same name')
                        name = name_and_design[0]
                        designs.append(name_and_design[1])

                yield name, designs

    def __next__(self):
        if len(self) == 1:
            raise StopIteration

        if len(self.levels_and_designs) == 1:
            return self.branches

        next_design = copy(self)
        next_design.levels_and_designs = next_design.levels_and_designs[1:]
        return next_design

    def __len__(self):
        length = len(self.levels_and_designs)
        if self.branches:
            length += len(list(self.branches.values())[0])
        return length

    def __getitem__(self, item):
        return self.levels_and_designs[item]

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__ == other.__dict__
        return False

    @staticmethod
    def first_pass(levels_and_designs):
        """
        Make a first pass of all designs in a |DesignTree|, from bottom to top.
        This calls |Design.first_pass| on every |Design| instance in the tree in the proper order,
        updating designs when a new IV is returned.
        This is necessary for |non-atomic orderings| because they modify the parent |Design|.

        """
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
        iv_names, iv_values = (), ()
        for design in levels_and_designs[0].design:
            iv_names, iv_values = design.first_pass()

        if iv_names != () or iv_values != ():
            raise ValueError('Cannot have a non-atomic ordering at the top level of a DesignTree. ')

    def add_base_level(self):
        """
        Adds a section to the top of the tree called ``'_base'``.
        This makes the |DesignTree| suitable for constructing an |Experiment|.

        Notes
        -----
        The |Experiment| constructor calls this automatically,
        and this shouldn't be called when appending a tree to an existing |Experiment|,
        so there is no use case for manually calling this method.

        """
        self.levels_and_designs.insert(0, Level('_base', Design()))
