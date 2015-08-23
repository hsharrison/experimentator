"""
This module contains the |ExperimentSection| class, which is imported in `__init__.py`.

"""
import collections
import itertools
import networkx as nx


class ExperimentSection:
    """
    A section of the experiment, at any level of the hierarchy.
    Single trials and groups of trials (blocks, sessions, participants, etc.)
    are represented as |ExperimentSection| instances.
    A complete experiment consists of |ExperimentSection| instances arranged in a tree.
    The root element should be an |Experiment| (a subclass of |ExperimentSection|);
    the rest of the sections can be reached via its descendants (see below on the sequence protocol).
    A new |ExperimentSection| instance is automatically populated with |ExperimentSection| descendants
    according to the |DesignTree| passed to its constructor.

    |ExperimentSection| implements Python's sequence protocol;
    its contents are |ExperimentSection| instances at the level below.
    In other words, children can be accessed using the ``[index]`` notation,
    as well as with slices (``[3:6]``) or iteration (``for section in experiment_section``).
    However, |ExperimentSection| breaks the Python convention of 0-based indexing,
    using 1-based indexing to match the convention in experimental science.

    The direct constructor is used to create an arbitrary |ExperimentSection|
    (i.e., possibly reloading an in-progress section),
    whereas |ExperimentSection.new| creates a section that hasn't yet started.

    Attributes
    ----------
    tree : |DesignTree|
    data : |ChainMap|
    description : str
        The name and number of the section (e.g., ``'trial 3'``).
    dataframe : |DataFrame|
        All data associated with the |ExperimentSection| and its descendants.
    heterogeneous_design_iv_name : str
        IV name determining which branch of the |DesignTree| to follow.
    level : str
        The level of the hierarchy at which this section lives.
    levels : list of str
        Level names below this section.
    local_levels : set
        Level names of this section's children. Usually a single-element set.
    is_bottom_level : bool
        If true, this is the lowest level of the hierarchy.
    is_top_level : bool
        If true, this is the highest level of the hierarchy (likely an |Experiment|).
    has_started: bool
        Whether this section has started to be run.
    has_finished : bool
        Whether this section has finished running.

    Notes
    -------
    Use 1-based indexing to refer to |ExperimentSection| children,
    both when when using indexing or slicing with an |ExperimentSection|,
    and when identifying sections in keyword arguments to methods such as |ExperimentSection.subsection|.
    This better corresponds to the language commonly used by scientists to identify participants, trials, etc.

    """
    def __init__(self, tree, data=None, has_started=False, has_finished=False, _children=None):
        self.tree = tree
        self.data = data or collections.ChainMap()
        self.has_started = has_started
        self.has_finished = has_finished
        self._children = collections.deque() if _children is None else _children

    @classmethod
    def new(cls, tree, data=None):
        """Create a new |ExperimentSection|.

        Parameters
        ----------
        tree : |DesignTree|
            Describes the design of the experiment hierarchy.
        data : |ChainMap|
            All data to be associated with the |ExperimentSection|,
            including the values of independent variables,
            the section numbers indicating the section's location in the experiment,
            and any results associated with this section,
            arising from either the run callback of the |Experiment| or from the method |ExperimentSection.add_data|.
            `data` should be a  |collections.ChainMap|,
            which behaves like a dictionary but has a hierarchical organization such that
            children can access values from the parent but not vice-versa.

        """
        self = cls(tree, data)
        if not self.is_bottom_level:
            # Create the section tree. Creating any section also creates the sections below it.
            self.append_design_tree(self.get_next_tree(), _renumber=False)
            self._number_children()

        return self

    @property
    def level(self):
        return self.tree[0].name

    @property
    def is_bottom_level(self):
        return len(self.tree) == 1

    @property
    def is_top_level(self):
        return self.level not in self.data

    @property
    def heterogeneous_design_iv_name(self):
        return self.tree.levels_and_designs[0].design[0].heterogeneous_design_iv_name

    @property
    def dataframe(self):
        from pandas import DataFrame
        data = DataFrame(section.data for section in self.walk() if section.is_bottom_level)
        return data.set_index(self.levels)

    @property
    def levels(self):
        levels = []
        for section in self.walk():
            for level in section.local_levels:
                if level not in levels:
                    levels.append(level)
        return levels

    @property
    def local_levels(self):
        return {child.level for child in self}

    @property
    def description(self):
        try:
            n = ' {}'.format(self.data[self.level])
        except KeyError:
            n = ''
        return '{}{}'.format(self.level, n)

    @property
    def _solo_id(self):
        return self.level, 1 if self.is_top_level else self.data[self.level]

    @property
    def _saveworthy_data(self):
        combined = self.data.copy()
        combined.update(
            _has_started=self.has_started,
            _has_finished=self.has_finished,
        )
        if not self.is_top_level:
            del combined[self.level]
        return combined

    def __eq__(self, other):
        if isinstance(other, type(self)):
            # Workaround pandas issue
            # https://github.com/pydata/pandas/issues/7830
            try:
                return self.__dict__ == other.__dict__
            except ValueError:
                return False
        return False

    def _add_to_graph(self, graph, id_list=None):
        parent_id_list = id_list or []
        id_list = parent_id_list + [self._solo_id]

        graph.add_node(tuple(id_list), self._saveworthy_data)

        if parent_id_list:
            graph.add_edge(tuple(parent_id_list), tuple(id_list))

        for child in self:
            child._add_to_graph(graph, id_list)

    def as_graph(self):
        """
        Build a |networkx.DiGraph| out of the experiment structure, starting at this section.
        Nodes are sections and graphs are parent-child relations.
        Node data are non-duplicated entries in |ExperimentSection.data|.

        Returns
        -------
        |networkx.DiGraph|
        """

        graph = nx.DiGraph()
        self._add_to_graph(graph)
        return graph

    def get_next_tree(self):
        """
        Get a tree to use for creating child |ExperimentSection| instances.

        Returns
        -------
        |DesignTree|

        """
        next_tree = next(self.tree)
        if isinstance(next_tree, dict):
            return next_tree[self.data[self.heterogeneous_design_iv_name]]
        return next_tree

    def append_design_tree(self, tree, to_start=False, _renumber=True):
        """
        Append all sections associated with the top level of a |DesignTree|
        (and therefore also create descendant sections) to the |ExperimentSection|.

        Parameters
        ----------
        tree : |DesignTree|
            The tree to append.
        to_start : bool, optional
            If True, the sections will be inserted at the beginning of the section.
            If False (the default), they will be appended to the end.

        Notes
        -----
        After calling this method,
        the section numbers in the children's |ExperimentSection.data| attributes
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
        Create a new |ExperimentSection| (and its descendants)
        and append it as a child of the current |ExperimentSection|.

        Parameters
        ----------
        data : dict
            Data to be included in the new section's |ExperimentSection.data| |ChainMap|.
            Should include values of IVs at the section's level, for example.
        tree : |DesignTree|, optional
            If given, the section will be appended from the top level of `tree`.
            If not passed, the tree of the current section will be used.
            Note that this does not affect IV values; IV values must still be included in `data`.
        to_start : bool, optional
            If True, the new |ExperimentSection| will be appended to the beginning of the current section.
            If False (the default), it will be appended to the end.

        Notes
        -----
        After calling this method,
        the section numbers in the children's |ExperimentSection.data| attributes
        will be automatically replaced with the correct numbers.

        """
        if not tree:
            tree = self.get_next_tree()

        child_data = self.data.new_child()
        child_data.update(data)

        child = ExperimentSection.new(tree, child_data)
        if to_start:
            self._children.appendleft(child)
        else:
            self._children.append(child)

        if _renumber:
            self._number_children()

    def _number_children(self):
        for level in self.local_levels:
            children_at_level = [child for child in self if child.level == level]
            for i, child in enumerate(children_at_level):
                child.data.update({level: i + 1})

    def add_data(self, data):
        """
        Update the |ExperimentSection.data| |ChainMap|.
        This data will apply to this section and all child sections.
        This can be used, for example, to manually record a participant's age.

        Parameters
        ----------
        data : dict
            Elements to be added to |ExperimentSection.data|.

        """
        self.data.update(data)

    def subsection(self, **section_numbers):
        """
        Find a single, descendant |ExperimentSection| based on section numbers.

        Parameters
        ----------
        **section_numbers
            Keyword arguments describing which subsection to find
            Must include every level higher than the desired section.

        Returns
        -------
        |ExperimentSection|

        See Also
        --------
        experimentator.section.ExperimentSection.all_subsections

        Examples
        --------
        Assuming the levels of the experiment saved in ``'example.exp'`` are
        ``('participant', 'session', 'block', 'trial')``,
        this will return the third block of the second participant's first session:

        >>> from experimentator import Experiment
        >>> exp = Experiment.load('example.exp')
        >>> some_block = exp.subsection(participant=2, session=1, block=3)

        """
        key = lambda node: all(level in node.data and node.data[level] == number
                               for level, number in section_numbers.items())
        result = self.depth_first_search(key)
        if result:
            return result[-1]

        raise ValueError('Could not find specified section.')

    def all_subsections(self, **section_numbers):
        """
        Find all subsections in the experiment matching the given section numbers.

        Yields specified |ExperimentSection| instances.
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
        experimentator.section.ExperimentSection.subsection

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

    def find_first_not_run(self, at_level, by_started=True):
        """
        Search the experimental hierarchy,
        and return the first descendant |ExperimentSection| at `at_level`
        that has not yet been run.

        Parameters
        ----------
        at_level : str
            Which level to search.
        by_started : bool, optional
            If True (default), returns the first section that has not been started.
            Otherwise, finds the first section that has not finished.

        Returns
        -------
        |ExperimentSection|

        """
        key = lambda node: node.level == at_level

        if by_started:
            path_key = lambda node: not node.has_started
        else:
            path_key = lambda node: not node.has_finished

        result = self.depth_first_search(key, path_key=path_key)
        if result:
            return result[-1]

    def find_first_partially_run(self, at_level):
        """
        Search the experimental hierarchy,
        and return the first descendant |ExperimentSection| at `at_level`
        that has been started but not finished.

        Parameters
        ----------
        at_level : str
            Which level to search.

        Returns
        -------
        |ExperimentSection|

        """
        key = lambda node: node.level == at_level
        path_key = lambda node: node.has_started and not node.has_finished

        result = self.depth_first_search(key, path_key=path_key)
        if result:
            return result[-1]

    def breadth_first_search(self, key):
        """
        Breadth-first search starting from here.
        Returns the entire search path.

        Parameters
        ----------
        key : func
            Function that returns True or False when passed an |ExperimentSection|.

        Returns
        -------
        list of |ExperimentSection|

        """
        paths = collections.deque([[self]])
        while paths:
            path = paths.popleft()
            node = path[-1]
            if key(node):
                return path

            for child in node:
                paths.append(path.copy() + [child])

        return []

    def depth_first_search(self, key, path_key=None, _path=None):
        """
        Depth-first search starting from here.
        Returns the entire search path.

        Parameters
        ----------
        key : func
            Function that returns True or False when passed an |ExperimentSection|.
        path_key : func, optional
            Function that returns True or False when passed an |ExperimentSection|.
            If given, the search will proceed only via sections for which `path_key` returns True.

        Returns
        -------
        list of |ExperimentSection|

        """
        no_path_key_or_true = lambda node: not path_key or path_key(node)

        path = _path or [self]
        if key(path[-1]) and no_path_key_or_true(path[-1]):
            return path

        for child in path[-1]:
            if no_path_key_or_true(child):
                result = self.depth_first_search(key, path_key=path_key, _path=path + [child])
                if result:
                    return result

        return []

    def walk(self):
        """
        Walk the tree depth-first, starting from here.
        Yields this section and every descendant section.

        """
        yield self
        for child in self:
            yield from child.walk()

    def parent(self, section):
        """
        Find the parent of a section.

        Parameters
        ----------
        section : |ExperimentSection|
            The section to find the parent of.

        Returns
        -------
        |ExperimentSection|

        """
        parents = self.parents(section)
        if parents:
            return parents[-1]

    def parents(self, section):
        """
        Find all parents of a section, in top-to-bottom order.

        Parameters
        ----------
        section : |ExperimentSection|
            The section to find the parents of.

        Returns
        -------
        list of |ExperimentSection|

        """
        if section.level == '_base':
            return []

        return self.breadth_first_search(lambda node: section in node)

    def _convert_index_object(self, item):
        """
        Change an indexing object (slice or int) from using 1-based indexing to using 0-based indexing.

        """
        if isinstance(item, slice):
            try:
                return slice(self._convert_index(item.start), self._convert_index(item.stop), item.step)
            except IndexError:
                raise IndexError('Use 1-based indexing with ExperimentSection instances')

        # Tuples will be converted when they come through as individual indices.
        elif isinstance(item, tuple):
            return item

        else:
            return self._convert_index(item)

    @staticmethod
    def _convert_index(idx):
        if idx is None:
            return None

        if idx < 0:
            return idx

        if idx == 0:
            raise IndexError('Use 1-based indexing with ExperimentSection instances')

        return idx - 1

    def __len__(self):
        return len(self._children)

    def __getitem__(self, item):
        item = self._convert_index_object(item)

        if isinstance(item, slice):
            return list(itertools.islice(self._children, *item.indices(len(self))))

        elif isinstance(item, tuple):
            section = self
            for idx in item:
                section = section[idx]
            return section

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
