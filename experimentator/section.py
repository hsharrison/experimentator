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
        self.levels = list(zip(*self.tree.levels_and_designs))[0][1:]
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

    def subsection(self, **section_numbers):
        """Find single subsection by numbers.

        Finds a descendant `ExperimentSection` based on section numbers.

        Arguments
        ---------
        **section_numbers
            Keyword arguments describing which subsection to find. Must include every level higher than the desired
            section. This method will descend the experimental hierarchy until it can no longer determine how to
            proceed, at which point it returns the current `ExperimentSection`.

        Returns
        -------
        ExperimentSection
            The specified subsection.

        See Also
        --------
        Experiment.all_subsections : find all subsections matching a set of criteria

        Examples
        --------
        Assuming an `Experiment` named ``exp`` with levels ``['participant', 'session', 'block', 'trial']``:

        >>>some_block = exp.subsection(participant=2, session=1, block=3)

        """
        node = self
        for level in self.levels:
            if level in section_numbers:
                node = node[section_numbers[level]]
            else:
                break

        return node

    def all_subsections(self, **section_numbers):
        """Find multiple subsections by numbers.

        Finds all subsections in the experiment matching the given section numbers.

        Arguments
        ---------
        **section_numbers
            Keyword arguments describing what subsections to find. Keys are level names, values are ints or sequences of
            ints.

        Yields
        ------
        ExperimentSection
            The specified `ExperimentSection` instances. The returned sections will be at the lowest level given in
            `section_numbers`. When encountering levels that aren't in `section_numbers` before reaching its lowest
            level, all sections will be descended into.

        See Also
        --------
        Experiment.subsection : find a single subsection.

        Examples
        --------
        Assuming an `Experiment` named ``exp`` with levels ``['participant', 'session', 'block', 'trial']``:

        >>>all_first_sessions = exp.all_subsections(session=1)

        ``all_first_sessions`` will be the first session of every participant.

        >>>trials = exp.all_subsections(block=1, trial=2)

        ``trials`` will be the second trial of the first block in every session.

        >>>other_trials = exp.all_subsections(session=1, trial=[1, 2, 3])

        ``other_trials`` will be the first three trials of every block in the first session of every participant.

        """
        # The state of the recursion is passed in the keyword argument '_section'.
        section = section_numbers.pop('_section', self)

        if not section.is_bottom_level and section.tree[1][0] in section_numbers:
            # Remove the section from section_numbers...it needs to be empty to signal completion.
            numbers = section_numbers.pop(section.tree[1][0])

            if isinstance(numbers, int):  # Only one number specified.
                if section_numbers:  # We're not done.
                    yield from self.all_subsections(_section=section[numbers], **section_numbers)
                else:  # We're done.
                    yield section[numbers]

            else:  # Multiple numbers specified.
                if section_numbers:  # We're not done.
                    for n in numbers:
                        yield from self.all_subsections(_section=section[n], **section_numbers)
                else:  # We're done.
                    yield from (section[n] for n in numbers)
        else:
            # Section not specified but we're not done; descend into every child.
            for child in section:
                yield from self.all_subsections(_section=child, **section_numbers)

    def find_first_not_run(self, at_level, by_started=True, starting_at=None):
        """Find the first subsection that has not been run.

        Searches the experimental hierarchy, returning the first descendant `ExperimentSection` at `level` that has not
        been run.

        Arguments
        ---------
        at_level : str
            Which level to search.
        by_started : bool, optional
            If true (default), finds the first section that has not been started. Otherwise, finds the first section
            that has not finished.
        starting_at : ExperimentSection, optional
            Starts the search at the given `ExperimentSection`. Allows for finding the first section not run of a
            particular part of the experiment. For example, the first block not run of the second participant could be
            found by:

            >>> exp.find_first_not_run('block', starting_at=exp.subsection(participant=2))

        Returns
        -------
        ExperimentSection
            The first `ExperimentSection` satisfying the specified criteria.

        """
        if by_started:
            key = lambda x: not x.has_started
            descriptor = 'not started'
        else:
            key = lambda x: not x.has_finished
            descriptor = 'not finished'

        return self.find_first_top_down(key, at_level, starting_at=starting_at, descriptor=descriptor)

    def find_first_partially_run(self, at_level, starting_at=None):
        """Find the first subsection that has been partially run.

        Searches the experimental hierarchy, returning the first descendant `ExperimentSection` at `level` that has been
        started but not finished.

        Arguments
        ---------
        at_level : str
            Which level to search.
        starting_at : ExperimentSection, optional
            Starts the search at the given `ExperimentSection`. Allows for finding the first partially-run section of a
            particular part of the experiment.

        Returns
        -------
        ExperimentSection
            The first `ExperimentSection` satisfying the specified criteria.

        """
        return self.find_first_top_down(lambda x: x.has_started and not x.has_finished, at_level,
                                        starting_at=starting_at, descriptor='partially run')

    def find_first_top_down(self, key, at_level=None, starting_at=None, descriptor=''):
        """Find first section, top down.

        Returns a section such that ``key(section) == True``. Descends the hierarchy only via sections for which `key`
        also returns ``True``.

        Arguments
        ---------
        key : function
            A function that returns true or false when passed an `ExperimentSection`.
        at_level : str, optional
            Which level to return a section from. If not given, the lowest possible level will be used.
        start_at : ExperimentSection, optional
            Where in the tree to start searching.
        descriptor : str, optional
            A human-language description of the criterion printed in the log message.

        Returns
        -------
        ExperimentSection
            The first `ExperimentSection` satisfying the specified criterion.

        """
        node = starting_at or self
        if node.is_bottom_level or node.level == at_level:
            return node

        logger.info('Checking all children of a {}...'.format(node.level))
        for child in node:
            if key(child):
                return self.find_first_top_down(key, at_level=at_level, starting_at=child, descriptor=descriptor)

        logger.warning('Could not find a child {}'.format(descriptor))

        if at_level is None:
            return node

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

    @property
    def dataframe(self):
        """Get data in dataframe format.

        Returns
        -------
        pandas.DataFrame
            A `DataFrame` containing all of the `ExperimentSection`'s data. The `DataFrame` will be MultiIndexed, with
            section numbers as indexes. Independent variables will also be included as columns.

        """
        from pandas import DataFrame
        data = DataFrame(self.generate_data()).set_index(list(self.levels))
        return data

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
