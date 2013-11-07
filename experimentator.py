# Copyright (c) 2013 Henry S. Harrison

import itertools
import collections
import logging
import pickle
import random
import pandas as pd


class QuitSession(BaseException):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


def load_experiment(file):
    with open(file, 'r') as f:
        return pickle.load(f)


def run_experiment_section(file, **kwargs):
    exp = load_experiment(file)
    try:
        exp.run(exp.find_section(**kwargs))
    except QuitSession as e:
        logging.warning('Quit event detected: {}.'.format(str(e)))
    finally:
        exp.save(file)


def export_experiment_data(experiment_file, data_file):
    exp = load_experiment(experiment_file)
    exp.export_data(data_file)


def section_sort(seq, method=None, n=1):
    if method == 'random':
        new_seq = n*seq
        random.shuffle(new_seq)
        yield from new_seq
    #TODO: More sorts (e.g. counterbalance)
    elif isinstance(method, str):
        raise TypeError('Unrecognized sort method {}.'.format(method))
    elif not method:
        yield from n*seq
    else:
        yield from n * seq[method]


class ExperimentSection():
    """
    Each ExperimentSection is responsible for managing the sections immediately below it.
    """
    def __init__(self, context, levels, ivs, sort, repeats):
        self.children = []
        self.context = context
        self.level = levels[0]
        self.results = None
        self.is_bottom_level = self.level == levels[-1]
        if self.is_bottom_level:
            self.next_level = None
            self.next_ivs = None
            self.next_sort = None
            self.next_repeats = None
            self.next_level_inputs = None
        else:
            self.next_level = levels[1]
            self.next_ivs = ivs.get(self.next_level, [])
            self.next_sort = sort.get(self.next_level)
            self.next_repeats = repeats.get(self.next_level, 1)
            self.next_level_inputs = (levels[1:], ivs, sort, repeats)

            for i, section_context in enumerate(self.get_contexts()):
                child_context = self.context.new_child()
                child_context.update(section_context)
                child_context[self.next_level] = i+1
                logging.debug('Generating {}.'.format(child_context))
                self.children.append(ExperimentSection(child_context, *self.next_level_inputs))

    def get_contexts(self):
        iv_tuples = itertools.product(*[v for v in self.next_ivs.values()])
        next_section_types = [{k: v for k, v in zip(self.next_ivs, condition)} for condition in iv_tuples]
        logging.debug('Sorting {}.'.format(self.next_level))
        yield from section_sort(next_section_types, method=self.next_sort, n=self.next_repeats)

    def add_child_ad_hoc(self, **kwargs):
        child_context = self.context.new_child()
        child_context[self.next_level] = self.children[-1][self.next_level] + 1
        child_context.update({k: random.choice(v) for k, v in self.next_ivs.items()})
        child_context.update(kwargs)
        self.children.append(ExperimentSection(child_context, *self.next_level_inputs))


class Experiment(metaclass=collections.abc.ABCMeta):
    def __init__(self, ivs_by_level, repeats_by_level, sort_by_level,
                 levels=('participant', 'session', 'block', 'trial'),
                 experiment_file=None,
                 output_names=None,
                 ):
        for level in collections.ChainMap([ivs_by_level, sort_by_level, repeats_by_level]):
            if level not in levels:
                raise TypeError('Unknown level {}.'.format(level))

        self.levels = levels
        self.ivs_by_level = ivs_by_level
        self.sort_by_level = sort_by_level
        self.repeats_by_level = repeats_by_level
        self.output_names = output_names

        actual_levels = ['root']
        actual_levels.extend(self.levels)
        self.root = ExperimentSection(
            collections.ChainMap(), actual_levels, self.ivs_by_level, self.sort_by_level, self.repeats_by_level)

        if experiment_file:
            self.save(experiment_file)
        else:
            logging.warning('No experiment_file provided, not saving Experiment instance.')

    @property
    def data(self):
        data = pd.DataFrame(self.generate_data(self.root), columns=self.output_names).set_index(self.levels)
        return data

    def save(self, filename):
        logging.debug('Saving Experiment instance to {}.'.format(filename))
        with open(filename, 'w') as f:
            pickle.dump(self, f)

    def generate_data(self, node):
        for child in node.children:
            if child.is_bottom_level:
                yield child.results
            else:
                yield from self.generate_data(child)

    def export_data(self, filename):
        with open(filename, 'w') as f:
            self.data.to_csv(f)

    def find_section(self, **kwargs):
        node = self.root
        for level in self.levels:
            if level in kwargs:
                logging.debug('Found specified {}.'.format(level))
                node = node.children[kwargs[level]-1]
            else:
                logging.info('No {} specified, returning previous level.'.format(level))
                return node

    def add_section(self, **kwargs):
        find_section_kwargs = {}
        for k in kwargs:
            if k in self.levels:
                find_section_kwargs[k] = kwargs.pop(k)
        self.find_section(**find_section_kwargs).add_child_ad_hoc(**kwargs)

    def run(self, section):
        logging.debug('Running {} with context {}.'.format(section.level, section.context))
        if section.is_bottom_level:
            section.results = self.run_trial(**section.context)
        else:
            self.start(section.level, **section.context)
            for i, next_section in enumerate(section.children):
                if i:
                    self.inter(next_section.level, **next_section.context)
                self.run(next_section)
            self.end(section.level, **section.context)

    def start(self, level, **kwargs):
        pass

    def end(self, level, **kwargs):
        pass

    def inter(self, level, **kwargs):
        pass

    @collections.abc.abstractmethod
    def run_trial(self, **_):
        return None, None