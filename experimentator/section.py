# Copyright (c) 2014 Henry S. Harrison
import random
import logging


class ExperimentSection():
    def __init__(self, context, levels, designs_by_level):
        self.context = context
        self.level = levels[0]
        self.designs = designs_by_level[self.level]
        self.is_bottom_level = self.level == levels[-1]

        self.children = []
        self.has_started = False
        self.has_finished = False
        if self.is_bottom_level:
            self.next_level = None
            self.next_design = None
            self.next_level_inputs = None

        else:  # Not bottom level.
            self.next_level = levels[1]
            self.next_designs = designs_by_level[self.next_level]
            self.next_level_inputs = (levels[1:], designs_by_level)

            # Create the section tree. Creating any section also creates the sections below it.
            for design in self.next_designs:
                self.append_design(design)

    def append_design(self, design):
        for new_context in design.order(**self.context):
            self.append_child(**new_context)

    def append_child(self, **context):
        child_context = self.context.new_child()
        child_context.update(context)
        child_context[self.next_level] = len(self) + 1
        logging.debug('Generating {} with context {}.'.format(self.next_level, child_context))
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

    def __len__(self):
        return len(self.children)

    def __getitem__(self, item):
        return self.children[item]
