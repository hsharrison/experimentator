# Copyright (c) 2014 Henry S. Harrison
import random
import logging


class ExperimentSection():
    """
    A section of an experiment, e.g. session, block, trial.
    Each ExperimentSection is responsible for managing its children, sections immediately below it. For example, in the
    default hierarchy, a block manages trials. An ExperimentSection maintains a context, a ChainMap containing all the
    independent variable values that apply to all of its children.

    Attributes:
        children:          A list of ExperimentSection instances.
        context:           A ChainMap of IV name: value mappings that apply to all of the section's children. Contains
                           results as well, if the section is at the lowest level.
        level:             The current level.
        is_bottom_level:   True if this section is at the lowest level of the tree (a trial in the default hierarchy).
        next_level:        The next level.
        next_settings:     The next settings, a dict with keys 'ivs' and 'ordering'.
        next_level_inputs: the inputs to be passed when constructing children.
        has_children:      True if the section has started to be run.
        has_finished:      True if the section has finished running.

    """
    def __init__(self, context, levels, settings_by_level):
        """
        Initialize an ExperimentSection. Creating an ExperimentSection also creates all its descendant sections.

        Args:
            context:            A ChainMap containing all the IV name: value mapping that apply to this section and all
                                its children. Set by the parent section.
            levels:             A list of names in the hierarchy, with levels[0] being the name of this section, and the
                                levels[1:] the names of its descendants.
            settings_by_level:  A mapping from the elements of levels to dicts with keys:
                                ivs:   independent variables, as mapping from names to possible values.
                                ordering:  Ordering subclass instance.

        """
        self.has_started = False
        self.has_finished = False
        self.children = []
        self.context = context
        self.level = levels[0]
        self.is_bottom_level = self.level == levels[-1]
        if self.is_bottom_level:
            self.next_level = None
            self.next_settings = None
            self.next_level_inputs = None

        else:  # Not bottom level.
            self.next_level = levels[1]
            self.next_settings = settings_by_level[self.next_level]
            self.next_level_inputs = (levels[1:], settings_by_level)

            # Create the section tree. Creating any section also creates the sections below it.
            for i, new_context in enumerate(self.next_settings['ordering'].order(**self.context)):
                child_context = self.context.new_child()
                child_context.update(new_context)
                child_context[self.next_level] = i+1
                logging.debug('Generating {} with context {}.'.format(self.next_level, child_context))
                self.children.append(ExperimentSection(child_context, *self.next_level_inputs))

    def add_child_ad_hoc(self, **kwargs):
        """
        Add an extra child to the section.

        Args:
            **kwargs: IV name=value assignments to determine the child's context. Any IV name not specified here will
                      be chosen randomly from the IV's possible values.
        """
        child_context = self.context.new_child()
        child_context[self.next_level] = self.children[-1][self.next_level] + 1
        child_context.update({k: random.choice(v) for k, v in self.next_settings.get('ivs', dict()).items()})
        child_context.update(kwargs)
        self.children.append(ExperimentSection(child_context, *self.next_level_inputs))

    def add_data(self, **kwargs):
        """
        Add data to all trials in a section. For example, add participant information to all entries under that
        participant.
        """
        self.context.update(kwargs)

    def generate_data(self):
        for child in self.children:
            if child.is_bottom_level:
                yield child.context
            else:
                yield from child.generate_data()
