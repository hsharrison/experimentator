"""ExperimentSection module.

Contains the `ExperimentSection` class, which is imported in `__init__.py`.

"""
import logging
import collections
import itertools

logger = logging.getLogger(__name__)


class ExperimentSection():
    """A section of an experiment.

    An `ExperimentSection` is a section of the experiment, at any level of the hierarchy. It may be a single trial, or
    any grouping of trials (a block, a session, a participant, etc.). An `Experiment` is a set of `ExperimentSection`
    instances, arranged in a tree. There is one base section (`Experiment.base_section`); the rest of the sections
    are descendants of the base section and can be reached through it (see below on the sequence protocol).

    When creating a new `Experiment` instance, it is automatically populated with a base `ExperimentSection` instance
    and descendants. The only use case of creating an `ExperimentSection` instance otherwise is to construct complicated
    experiments by appending new `ExperimentSection` instances to some sections but not others. In this way an
    experiment can be created that contains different designs in different places.

    `ExperimentSection` implements Python's sequence protocol; its items are `ExperimentSection` instances at the level
    below. This means children can be accessed directly on the `ExperimentSection` instance using the ``[index]``
    notation. Slices (e.g., ``[3:6]``) and iteration (``for section in my_experiment_section``) are also supported.
    However, `ExperimentSection` breaks the Python convention of 0-based indexing. It uses 1-based indexing to match the
    convention in experimental science.

    When creating a new `ExperimentSection`, its descendants are automatically created as well.

    Arguments
    ---------
    tree : DesignTree
        A `DesignTree` object, describing the design of the experiment hierarchy (containing the `Design` at the current
        level all levels below).
    data : ChainMap
        All data associated with the `ExperimentSection` and all its parents, including the values of independent
        variables, the section numbers indicating the section's location in the experiment, and any results associated
        with this section, arising from either the run callback of the `Experiment`, or the `ExperimentSection.add_data`
        method. `data` is a `ChainMap`, which behaves like a dictionary but has a hierarchical organization such that
        children can access values from the parent but not vice-versa.

    Attributes
    ----------
    tree : DesignTree
    data : ChainMap
    level : str
        The level of the hierarchy at which this section lives.
    is_bottom_level : bool
        If true, this is the lowest level of the hierarchy.
    has_start : bool
        Whether this section has started to be run.
    has_finished : bool
        Whether this section has finished running.

    Warning
    -------
    Use 1-based indexing to refer to `ExperimentSection` children, both when identifying sections in keyword arguments
    to certain methods (e.g., `Experiment.section`) and when using the sequence protocol on an `ExperimentSection`
    instance.

    """
    def __init__(self, tree, data):
        self.data = data
        self.tree = tree
        self.level = self.tree[0][0]
        self.is_bottom_level = len(self.tree) == 1

        self._children = collections.deque()
        self.has_started = False
        self.has_finished = False

        if not self.is_bottom_level:
            # Create the section tree. Creating any section also creates the sections below it.
            self.append_design_tree(next(self.tree), _renumber=False)
            self._number_children()

    def __repr__(self):
        return 'ExperimentSection({}, {})'.format(self.tree.__repr__(), self.data.__repr__())

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__ == other.__dict__

    def append_design_tree(self, tree, to_start=False, _renumber=True):
        """Append sections to this section's children.

        This method appends all sections associated with the top level of a `DesignTree` instance (and therefore also
        creates descendant sections as well) to the `ExperimentSection` instance.

        Arguments
        ---------
        tree : DesignTree
            The `DesignTree` instance to append.
        to_start : bool, optional
            If true, the sections will be appended to the beginning of the section. If False (the default), they will be
            appended to the end.

        Note
        ----
        After calling `ExperimentSection.append_design_tree`, the section numbers in the data of the child sections
        will be automatically replaced with the correct numbers.

        """
        level, designs = tree.levels_and_designs[0]

        if self.level == level:
            raise ValueError('DesignTree to be appended is at the same level as the current section')

        if to_start:
            for design in reversed(designs):
                for new_data in reversed(design.get_order(self.data)):
                    self.append_child(new_data, tree=tree, to_start=True, _renumber=False)

        else:
            for design in designs:
                for new_data in design.get_order(self.data):
                    self.append_child(new_data, tree=tree, _renumber=False)

        if _renumber:
            self._number_children()

    def append_child(self, data, tree=None, to_start=False, _renumber=True):
        """Append a single section to this section's children.

        This method appends a single section to the `ExperimentSection` instance. In the process, its children are
        created as well.

        Arguments
        ---------
        data : dict
            Data to be included in the new section's `ExperimentSection.data` `ChainMap`. Should include values of IVs
            at the section's level, for example.
        tree : DesignTree, optional
            If given, the section will be appended from the top level of `tree`. If not passed, the tree of the current
            section will be used. Note that this does not affect IV values; IV values must be included in `data`.
        to_start : bool, optional
            If true, the section will be appended to the beginning of the section. If False (the default), it will be
            appended to the end.

        Note
        ----
        After calling `ExperimentSection.append_child`, the section numbers in the data of the child sections will
        be automatically replaced with the correct numbers.

        """
        if not tree:
            tree = next(self.tree)

        child_data = self.data.new_child()
        child_data.update(data)
        level = tree.levels_and_designs[0][0]

        logger.debug('Generating {} with data {}.'.format(level, child_data))
        child = ExperimentSection(tree, child_data)
        if to_start:
            self._children.appendleft(child)
        else:
            self._children.append(child)

        if _renumber:
            self._number_children()

    def _number_children(self):
        levels = {child.level for child in self}
        for level in levels:
            children_at_level = [child for child in self if child.level == level]
            for i, child in enumerate(children_at_level):
                child.data.update({level: i + 1})

    def add_data(self, data):
        """Add data.

        This method updates the `ExperimentSection.data` `ChainMap` according to the items in `data`. Use this, for
        example, to define data to apply to this section and all child sections, for example to record a participant's
        age.

        Arguments
        ---------
        data : dict
            Elements to be included in the `ExperimentSection.data` `ChainMap`.

        """
        self.data.update(data)

    def generate_data(self):
        """Generate data.

        Yields
        ------
        ChainMap
            data of all bottom-level sections that are descendants of this section.

        """
        for child in self:
            if child.is_bottom_level:
                yield child.data
            else:
                yield from child.generate_data()

    @staticmethod
    def _prepare_for_indexing(item):
        """Change an indexing object from using 1-based indexing to using 0-based indexing.

        """
        if isinstance(item, slice):
            if item.start == 0 or item.stop == 0:
                raise IndexError('Use 1-based indexing with ExperimentSection instances')
            return slice(item.start-1 if item.start else None, item.stop-1 if item.stop else None, item.step)

        elif item == 0:
            raise IndexError('Use 1-based indexing with ExperimentSection instances')

        elif item == -1:
            return item

        else:
            return item - 1

    def __len__(self):
        return len(self._children)

    def __getitem__(self, item):
        item = self._prepare_for_indexing(item)

        if isinstance(item, slice):
            return list(itertools.islice(self._children, *item.indices(len(self))))
        else:
            return self._children[item]

    def __bool__(self):
        return True

    def __iter__(self):
        return self._children.__iter__()

    def __delitem__(self, key):
        del self._children[self._prepare_for_indexing(key)]
        self._number_children()

    def __setitem__(self, key, value):
        self._children[self._prepare_for_indexing(key)] = value
        self._number_children()

    def __reversed__(self):
        return reversed(self._children)

    def __contains__(self, item):
        return item in self._children
