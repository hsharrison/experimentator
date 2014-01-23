# Copyright (c) 2014 Henry S. Harrison
import itertools
import random
import logging


def _unique_iv_combinations(ivs):
    """
    Crosses the section's independent variables, and yields the unique combinations.
    """
    try:
        iv_names, iv_values = zip(*ivs.items())
    except ValueError:
        # Workaround because zip doesn't want to return two elements if ivs is empty.
        iv_names = ()
        iv_values = ()
    iv_combinations = itertools.product(*iv_values)

    for iv_combination in iv_combinations:
        yield dict(zip(iv_names, iv_combination))


def _non_atomic_orders(levels, settings_by_level):
    for level, next_level in zip(levels[:-1], levels[1:]):
        sort = settings_by_level[next_level].get('sort')

        if sort == 'complete-counterbalance':
            next_level_ivs = settings_by_level[next_level].get('ivs', {})
            sections = settings_by_level[next_level].get('n', 1) * list(_unique_iv_combinations(next_level_ivs))
            permutations = list(itertools.permutations(sections))
            ivs = settings_by_level[level].get('ivs', {})
            ivs.update(order=permutations)
            settings_by_level[level].update(ivs)
            settings_by_level[next_level].update(sort='non-atomic')

        elif sort == 'latin-square':
            # TODO: implement
            pass

    return settings_by_level


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
        next_settings:     The next settings, a dict with keys 'ivs', 'sort', and 'n'.
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
                                ivs:   independent variables, as mapping from names to possible values
                                sort:  string (e.g., 'random') or None
                                n:     number of repeats of each unique combination of ivs
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
        else:
            # Handle non-atomic sorts
            settings_by_level = _non_atomic_orders(levels, settings_by_level)

            self.next_level = levels[1]
            self.next_settings = settings_by_level.get(self.next_level, dict())
            self.next_level_inputs = (levels[1:], settings_by_level)

            # Create the section tree. Creating any section also creates the sections below it
            unique_contexts = list(_unique_iv_combinations(self.next_settings.get('ivs', {})))
            for i, new_context in enumerate(self.sort_and_repeat(unique_contexts)):
                child_context = self.context.new_child()
                child_context.update(new_context)
                child_context[self.next_level] = i+1
                logging.debug('Generating {} with context {}.'.format(self.next_level, child_context))
                self.children.append(ExperimentSection(child_context, *self.next_level_inputs))

    def sort_and_repeat(self, unique_contexts):
        """
        Sorts and repeats the unique contexts for children of the section.

        Args:
            unique_contexts: A sequence of unique ChainMaps describing the possible combinations of the independent
                             variables at the section's level.

        Yields the sorted and repeated contexts, according to the section's sort and n entries in its next_level_dict
        attribute.
        """
        method = self.next_settings.get('sort', None)
        n = self.next_settings.get('n', 1)

        if not method:
            yield from n * unique_contexts

        elif method == 'random':
            new_seq = n * unique_contexts
            random.shuffle(new_seq)
            yield from new_seq

        elif method == 'non-atomic':
            yield from self.context['order']

        elif method == 'ordered':
            if len(unique_contexts[0]) != 1:
                raise ValueError("More than one independent variable at level with sort method 'ordered'")
            if 'order' not in self.context or self.context['order'] not in ('ascending', 'descending'):
                logging.warning("Sort method 'ordered' used without specifying ascending or descending order. " +
                                "Defaulting to ascending.")
                reverse_sort = False
            else:
                reverse_sort = self.context['order'] == 'descending'
            yield from sorted(unique_contexts, key=lambda c: list(c.values())[0], reverse=reverse_sort)

        else:
            raise ValueError('Unrecognized sort method {}.'.format(method))

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
