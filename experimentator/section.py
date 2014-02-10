"""ExperimentSection module.

Contains the `ExperimentSection` class, which is imported in `__init__.py`.

"""
import logging
import collections


class ExperimentSection():
    """A section of an experiment.

    An `ExperimentSection` is a section of the experiment, at any level of the hierarchy. It may be a single trial, or
    any grouping of trials (a block, a session, a participant, etc.). An `Experiment` is a set of `ExperimentSection`
    instances, arranged in a tree. There is one base section (`Experiment.base_section`); the rest of the sections
    are descendants of the base section and can be reached via repeated accesses of the `ExperimentSection.children`
    attribute.

    When creating a new `Experiment` instance, it is automatically populated with a base `ExperimentSection` instance
    and descendants. The only use case of creating an `ExperimentSection` instance otherwise is to construct complicated
    experiments by appending new `ExperimentSection` instances to some sections but not others. In this way an
    experiment can be created that contains different designs in different places.

    When creating a new `ExperimentSection`, its descendants are automatically created as well.

    Arguments
    ---------
    tree : DesignTree
        A `DesignTree` object, describing the design of the experiment hierarchy (containing the `Design` at the current
        level all levels below).
    context : ChainMap
        The context of the `ExperimentSection` is all data associated with it, including the values of independent
        variables associated with this level and levels above, the section numbers indicating the section's location in
        the experiment, and any results associated with this section, arising from either the run callback of the
        `Experiment`, or the `ExperimentSection.add_data` method. The `context` is a `ChainMap`, which behaves like a
        dictionary but has a hierarchical organization such that children can access values from the parent but not
        vice-versa.

    Attributes
    ----------
    tree : DesignTree
    context : ChainMap
    level : str
        The level of the hierarchy at which this section lives.
    is_bottom_level : bool
        If true, this is the lowest level of the hierarchy.
    children : deque of ExperimentSection
        Children `ExperimentSection` instances at the level below.
    has_start : bool
        Whether this section has started to be run.
    has_finished : bool
        Whether this section has finished running.

    """
    def __init__(self, tree, context):
        self.context = context
        self.tree = tree
        self.level = self.tree[0][0]
        self.is_bottom_level = len(self.tree) == 1

        self.children = collections.deque()
        self.has_started = False
        self.has_finished = False

        if self.is_bottom_level:
            self._next_level = None
            self._next_designs = None

        else:  # Not bottom level.
            self._next_level, self._next_designs = self.tree[1]

            # Create the section tree. Creating any section also creates the sections below it.
            for design in self._next_designs:
                self.append_design(design)

    def append_design(self, design, to_start=False):
        """Append sections to this section's children.

        This method appends all sections associated with a `Design` instance to the `ExperimentSection.children`
        attribute.

        Arguments
        ---------
        design : Design
            The `Design` instance to append.
        to_start : bool, optional
            If true, the sections will be appended to the beginning of `ExperimentSection.children`. If False (the
            default), they will be appended to the end.

        Note
        ----
        After calling `ExperimentSection.append_design`, the section numbers in the context of the child sections will
        be automatically replaced with the correct numbers.

        """
        if to_start:
            for new_context in reversed(design.order(**self.context)):
                self.append_child(to_start=True, **new_context)

        else:
            for new_context in design.order(**self.context):
                self.append_child(**new_context)

    def append_child(self, to_start=False, **context):
        """Append a single section to this section's children.

        This method appends a single section to the `ExperimentSection.children` attribute.

        Arguments
        ---------
        to_start : bool, optional
            If true, the section will be appended to the beginning of `ExperimentSection.children`. If False (the
            default), it will be appended to the end.
        **context
            Arbitrary keywords to be included in the new section's `ExperimentSection.context` `ChainMap`. Should
            include values of IVs at the section's level, for example.

        Note
        ----
        After calling `ExperimentSection.append_child`, the section numbers in the context of the child sections will
        be automatically replaced with the correct numbers.

        """
        child_context = self.context.new_child()
        child_context.update(context)

        logging.debug('Generating {} with context {}.'.format(self._next_level, child_context))
        child = ExperimentSection(next(self.tree), child_context)
        if to_start:
            self.children.appendleft(child)
        else:
            self.children.append(child)

        self._number_children()

    def _number_children(self):
        for i, child in enumerate(self.children):
            child.context.update({self._next_level: i + 1})

    def add_data(self, **data):
        """Add data.

        This method updates the `ExperimentSection.context` `ChainMap` according to the items in `data`. Use this, for
        example, to define data to apply to this section and all child sections, for example to record a participant's
        age.

        Arguments
        ---------
        **data
            Arbitrary keyword arguments to be included in the `ExperimentSection.context` `ChainMap`.

        """
        self.context.update(data)

    def _generate_data(self):
        for child in self.children:
            if child.is_bottom_level:
                yield child.context
            else:
                yield from child._generate_data()

    def __len__(self):
        return len(self.children)

    def __getitem__(self, item):
        return self.children[item]
