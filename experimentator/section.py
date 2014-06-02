"""
This module contains the `ExperimentSection` class,
which is imported in `__init__.py`.

"""
import logging
import collections
import itertools

logger = logging.getLogger(__name__)


class ExperimentSection():
    """
    A section of the experiment, at any level of the hierarchy.
    Single trials,  groups of trials (blocks, sessions, participants, etc.)
    are represented as :class:`ExperimentSection` instances.
    A complete experiment consists of :class:`ExperimentSection` instances arranged in a tree.
    The root element should be an :class:`Experiment <experimentator.experiment.Experiment>` instance
    (a subclass of :class:`ExperimentSection`);
    the rest of the sections can be reached via its descendants (see below on the sequence protocol).
    A new :class:`ExperimentSection` instance
    is automatically populated with :class:`ExperimentSection` descendants
    according to the :class:`DesignTree <experimentator.design.DesignTree>` passed to its constructor.

    :class:`ExperimentSection` implements Python's sequence protocol;
    its items are :class:`ExperimentSection` instances at the level below.
    In other words, children can be accessed using the ``[index]`` notation,
    as we as using slices (``my_experiment_section[3:6]``) or
    iteration (``for section in my_experiment_section:``).
    However, `ExperimentSection` breaks the Python convention of 0-based indexing.
    It uses 1-based indexing to match the convention in experimental science.

    Parameters
    ----------
    tree : :class:`DesignTree <experimentator.design.DesignTree>`
        Describes the design of the experiment hierarchy.
    data : :class:`~collections.ChainMap`
        All data to be associated with the :class:`ExperimentSection`,
        including the values of independent variables,
        the section numbers indicating the section's location in the experiment,
        and any results associated with this section,
        arising from either the run callback of the :class:`Experiment <experimentator.experiment.Experiment>`,
        or from the method :meth:`ExperimentSection.add_data`.
        `data` should be a  :class:`collections.ChainMap`,
        which behaves like a dictionary but has a hierarchical organization such that
        children can access values from the parent but not vice-versa.

    Attributes
    ----------
    tree : :class:`DesignTree <experimentator.design.DesignTree>`
    data : :class:`~collections.ChainMap`
    dataframe
    heterogeneous_design_iv_name
    level : str
        The level of the hierarchy at which this section lives.
    is_bottom_level : bool
        If true, this is the lowest level of the hierarchy.
    has_start : bool
        Whether this section has started to be run.
    has_finished : bool
        Whether this section has finished running.

    Notes
    -------
    Use 1-based indexing to refer to :class:`ExperimentSection` children,
    both when when using indexing or slicing with an :class:`ExperimentSection`,
    and when identifying sections in keyword arguments to methods
    such as :meth:`ExperimentSection.subsection`.
    This better corresponds to the language commonly used by scientists to identify participants, trials, etc.

    """
    def __init__(self, tree, data):
        self.data = data
        self.tree = tree
        self.level = self.tree[0].name
        self.levels = [level.name for level in self.tree.levels_and_designs][1:]
        self.is_bottom_level = len(self.tree) == 1

        self._children = collections.deque()
        self.has_started = False
        self.has_finished = False

        if not self.is_bottom_level:
            # Create the section tree. Creating any section also creates the sections below it.
            self.append_design_tree(self.get_next_tree(), _renumber=False)
            self._number_children()

    @property
    def heterogeneous_design_iv_name(self):
        """
        (str) IV name determining which branch of the :class:`DesignTree <experimentator.design.DesignTree>` to follow.

        """
        return self.tree.levels_and_designs[0].design[0].heterogeneous_design_iv_name

    @property
    def dataframe(self):
        """
        (:class:`~pandas.DataFrame`) All data associated with the :class:`ExperimentSection` and its parents.

        """
        from pandas import DataFrame
        data = DataFrame(self.generate_data()).set_index(list(self.levels))
        return data

    def __repr__(self):
        return 'ExperimentSection({}, {})'.format(self.tree.__repr__(), self.data.__repr__())

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__ == other.__dict__

    def get_next_tree(self):
        """
        Get a tree to use for creating child :class:`ExperimentSection` instances.

        Returns
        -------
        :class:`DesignTree <experimentator.design.DesignTree>`

        """
        next_tree = next(self.tree)
        if isinstance(next_tree, dict):
            return next_tree[self.data[self.heterogeneous_design_iv_name]]
        return next_tree

    def append_design_tree(self, tree, to_start=False, _renumber=True):
        """
        Append all sections associated with the top level of a :class:`DesignTree <experimentator.design.DesignTree>`
        (and therefore also create descendant sections)
        to the :class:`ExperimentSection`.

        Parameters
        ----------
        tree : :class:`DesignTree <experimentator.design.DesignTree>`
            The tree to append.
        to_start : bool, optional
            If True, the sections will be inserted at the beginning of the section.
            If False (the default), they will be appended to the end.

        Notes
        -----
        After calling this method,
        the section numbers in the children's :attr:`ExperimentSection.data` attributes
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
        """
        Create a new :class:`ExperimentSection` (and its descendants)
        and append it as a child of the current :class:`ExperimentSection`.

        Parameters
        ----------
        data : dict
            Data to be included in the new section's :attr:`ExperimentSection.data` :class:`~collections.ChainMap`.
            Should include values of IVs at the section's level, for example.
        tree : :class:`DesignTree <experimentator.design.DesignTree>`, optional
            If given, the section will be appended from the top level of `tree`.
            If not passed, the tree of the current section will be used.
            Note that this does not affect IV values; IV values must still be included in `data`.
        to_start : bool, optional
            If True, the new :class:`ExperimentSection` will be appended to the beginning of the current section.
            If False (the default), it will be appended to the end.

        Notes
        -----
        After calling this method,
        the section numbers in the children's :attr:`ExperimentSection.data` attributes
        will be automatically replaced with the correct numbers.

        """
        if not tree:
            tree = self.get_next_tree()

        child_data = self.data.new_child()
        child_data.update(data)
        level = tree.levels_and_designs[0].name

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
        """
        Update the :attr:`ExperimentSection.data` :class:`~collections.ChainMap`.
        This data will apply to this section and all child sections.
        This can be used, for example, to manually record a participant's age.

        Parameters
        ----------
        data : dict
            Elements to be added to :attr:`ExperimentSection.data`.

        """
        self.data.update(data)

    def generate_data(self):
        """
        Yield the :attr:`ExperimentSection.data` attribute from each bottom-level section
        that descends from this section.

        """
        for child in self:
            if child.is_bottom_level:
                yield child.data
            else:
                yield from child.generate_data()

    def subsection(self, **section_numbers):
        """
        Find a single, descendant :class:`ExperimentSection` based on section numbers.

        Parameters
        ----------
        **section_numbers
            Keyword arguments describing which subsection to find
            Must include every level higher than the desired section.

        Returns
        -------
        :class:`ExperimentSection`

        See Also
        --------
        ExperimentSection.all_subsections

        Examples
        --------
        Assuming the levels of the experiment saved in ``'example.exp'`` are
        ``('participant', 'session', 'block', 'trial')``,
        this will return the third block of the second participant's first session:

        >>> from experimentator import Experiment
        >>> exp = Experiment.load('example.exp')
        >>> some_block = exp.subsection(participant=2, session=1, block=3)

        """
        if not section_numbers:
            return self

        for child in self:
            if (child.level in section_numbers and
                    child.data[child.level] == section_numbers[child.level]):
                del section_numbers[child.level]
                return child.subsection(**section_numbers)

        raise ValueError('Could not find specified section.')

    def all_subsections(self, **section_numbers):
        """
        Find all subsections in the experiment matching the given section numbers.

        Yields specified :class:`ExperimentSection` instances.
        The yielded sections will be at the lowest level given in `section_numbers`.
        If levels not in `section_numbers` are encountered before reaching its lowest level,
        all sections will be descended into.

        Parameters
        ----------
        **section_numbers
            Keyword arguments describing what subsections to find.
            Keys are level names, values are ints or sequences of ints.

        See Also
        --------
        ExperimentSection.subsection

        Examples
        --------
        Assuming the levels of the experiment saved in ``'example.exp'`` are
        ``('participant', 'session', 'block', 'trial')``:

        >>> from experimentator import Experiment
        >>> exp = Experiment.load('example.exp')

        Get the  first session of each participant:

        >>> all_first_sessions = list(exp.all_subsections(session=1))

        Get the second trial of the first block in each session:

        >>> trials = list(exp.all_subsections(block=1, trial=2))

        Get the first three trials of each block in the first session of each participant:

        >>> more_trials = list(exp.all_subsections(session=1, trial=[1, 2, 3]))

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
        """
        Search the experimental hierarchy,
        and return the first descendant :class:`ExperimentSection` at `at_level`
        that has not yet been run.

        Parameters
        ----------
        at_level : str
            Which level to search.
        by_started : bool, optional
            If True (default), returns the first section that has not been started.
            Otherwise, finds the first section that has not finished.
        starting_at : :class:`ExperimentSection`, optional
            Starts the search at the given section.
            Allows for finding the first section not run of a particular part of the experiment.
            For example, the first block not run of the second participant could be found by:

            >>> from experimentator import Experiment
            >>> exp = Experiment.load('experiment.exp')
            >>> some_block = exp.find_first_not_run(
            ...     'block', starting_at=exp.subsection(participant=2))

        Returns
        -------
        :class:`ExperimentSection`

        """
        if by_started:
            key = lambda x: not x.has_started
            descriptor = 'not started'
        else:
            key = lambda x: not x.has_finished
            descriptor = 'not finished'

        return self.find_first_top_down(key, at_level, starting_at=starting_at, descriptor=descriptor)

    def find_first_partially_run(self, at_level, starting_at=None):
        """
        Search the experimental hierarchy,
        and return the first descendant :class:`ExperimentSection` at `at_level`
        that has been started but not finished.

        Parameters
        ----------
        at_level : str
            Which level to search.
        starting_at : :class:`ExperimentSection`, optional
            Starts the search at the given section.
            Allows for finding the first partially-run section of a particular part of the experiment.

        Returns
        -------
        :class:`ExperimentSection`

        """
        return self.find_first_top_down(lambda x: x.has_started and not x.has_finished, at_level,
                                        starting_at=starting_at, descriptor='partially run')

    def find_first_top_down(self, key, at_level=None, starting_at=None, descriptor=''):
        """
        Search the experimental hierarchy starting at the top,
        and return the first :class:`ExperimentSection` ``section`` at `at_level`
        for which ``key(section)`` is True.
        Descends the hierarchy only via sections for which ``key(section)`` is True.

        Parameters
        ----------
        key : function
            A function that returns True or False when passed an :class:`ExperimentSection`.
        at_level : str, optional
            Which level to return a section from.
            If not given, the lowest possible level will be used.
        start_at : :class:`ExperimentSection`, optional
            Where in the tree to start searching.
        descriptor : str, optional
            A human-language description of the criterion, for logging.

        Returns
        -------
        :class:`ExperimentSection`

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

    def _convert_index_object(self, item):
        """
        Change an indexing object (slice or int) from using 1-based indexing to using 0-based indexing.

        """
        try:
            if isinstance(item, slice):
                return slice(self._convert_index(item.start), self._convert_index(item.stop), item.step)
            else:
                return self._convert_index(item)

        except IndexError:
            raise IndexError('Use 1-based indexing with ExperimentSection instances')

    @staticmethod
    def _convert_index(idx):
        if idx is None:
            return None

        if idx < 0:
            return idx

        if idx == 0:
            raise IndexError

        return idx - 1

    def __len__(self):
        return len(self._children)

    def __getitem__(self, item):
        item = self._convert_index_object(item)

        if isinstance(item, slice):
            return list(itertools.islice(self._children, *item.indices(len(self))))
        else:
            return self._children[item]

    def __bool__(self):
        return True

    def __iter__(self):
        return self._children.__iter__()

    def __delitem__(self, key):
        del self._children[self._convert_index_object(key)]
        self._number_children()

    def __setitem__(self, key, value):
        self._children[self._convert_index_object(key)] = value
        self._number_children()

    def __reversed__(self):
        return reversed(self._children)

    def __contains__(self, item):
        return item in self._children
