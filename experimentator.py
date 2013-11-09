"""
A module for running experiments.

The basic use case is that you have already written code to run a single trial and would like to run a set of
experimental sessions in which inputs to your trial function are systematically varied and repeated.


Copyright (c) 2013 Henry S. Harrison
"""

import itertools
import collections
import logging
import pickle
import random
import pandas as pd


class QuitSession(BaseException):
    """
    Raised to exit the experimental session.

    Raise this exception from inside a trial when the entire session should be exited, for example if the user presses
    a 'quit' key.

    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


def load_experiment(experiment_file):
    """
    Loads an experiment file. Returns the experiment instance.
    """
    with open(experiment_file, 'r') as f:
        return pickle.load(f)


def run_experiment_section(experiment_file, **kwargs):
    """
    Run an experiment instance from a file, and saves it. Monitors for QuitSession exceptions (If a QuitSession
    exception is raised, still saves the data. Running the section again will overwrite it.).
    """
    exp = load_experiment(experiment_file)
    try:
        exp.run(exp.find_section(**kwargs))
    except QuitSession as e:
        logging.warning('Quit event detected: {}.'.format(str(e)))
    finally:
        exp.save(experiment_file)


def export_experiment_data(experiment_file, data_file):
    """
    Reads a pickled experiment instance from experiment_file and saves its data in csv format to data_file.
    """
    load_experiment(experiment_file).export_data(data_file)


class ExperimentSection():
    """
    A section of an experiment, e.g. session, block, trial.

    Each ExperimentSection is responsible for managing its children, sections immediately below it. For example, in the
    default hierarchy, a block manages trials. An ExperimentSection maintains a context, a ChainMap containing all the
    independent variable values that apply to all of its children.

    Attributes:
        children: A list of ExperimentSection instances.
        context: A ChainMap of IV name: value mappings that apply to all of the section's children.
        level: The current level.
        results: Initially none, for the lowest level this is where the outputs of run_trial are stored, as a tuple.
        is_bottom_level: A boolean, True if this section is at the lowest level of the tree (a trial in the default
            hierarchy.
        next_level: The next level.
        next_settings: The next settings, a dict with keys 'ivs', 'sort', and 'n'.
        next_level_inputs: the inputs to be passed when constructing children.

    """
    def __init__(self, context, levels, settings_by_level):
        """
        Initialize an ExperimentSection.

        Args:
            context: A ChainMap containing all the IV name: value mapping that apply to this section and all its
                children. Set by the parent section.
            levels: A list of names in the hierarchy, with levels[0] being the name of this section, and the levels[1:]
                the names of its descendants.
            settings_by_level: A mapping from the elements of levels to dicts with keys:
                ivs: independent variables, as mapping from names to possible values
                sort: sort method, string (e.g., 'random'), sequence of indices, or None
                n: number of repeats of each unique combination of ivs
        """
        assert all(level in settings_by_level for level in levels[1:])
        assert all(level in levels[1:] for level in settings_by_level)
        self.children = []
        self.context = context
        self.level = levels[0]
        self.results = None
        self.is_bottom_level = self.level == levels[-1]
        if self.is_bottom_level:
            self.next_level = None
            self.next_settings = None
            self.next_level_inputs = None
        else:
            self.next_level = levels[1]
            self.next_settings = settings_by_level.pop(self.next_level)
            self.next_level_inputs = (levels[1:], settings_by_level)

            for i, section_context in enumerate(self.get_child_contexts()):
                child_context = self.context.new_child()
                child_context.update(section_context)
                child_context[self.next_level] = i+1
                logging.debug('Generating {}.'.format(child_context))
                self.children.append(ExperimentSection(child_context, *self.next_level_inputs))

    def get_child_contexts(self):
        """
        Crosses the section's independent variables, and sorts and repeats the unique combinations to yield the
        context for the section's children.
        """
        ivs = self.next_settings.get('ivs', dict())
        iv_combinations = itertools.product(*[v for v in ivs.values()])
        unique_contexts = [{k: v for k, v in zip(ivs, condition)} for condition in iv_combinations]
        logging.debug('Sorting {}.'.format(self.next_level))
        yield from self.sort_and_repeat(unique_contexts)

    def sort_and_repeat(self, unique_contexts):
        """
        Sorts and repeats the unique contexts for children of the section.

        Args:
            unique_contexts: A list of unique ChainMaps describing the possible combinations of the independent
               variables at the section's level.

        Yields the sorted and repeated contexts, according to the section's sort and n entries in its next_level_dict
            attribute.
        """
        method = self.next_settings.get('sort', None)
        n = self.next_settings.get('n', 1)
        if method == 'random':
            new_seq = n * unique_contexts
            random.shuffle(new_seq)
            yield from new_seq
        #TODO: More sorts (e.g. counterbalance)
        elif isinstance(method, str):
            raise TypeError('Unrecognized sort method {}.'.format(method))
        elif not method:
            yield from n * unique_contexts
        else:
            yield from n * unique_contexts[method]

    def add_child_ad_hoc(self, **kwargs):
        """
        Add an extra child to the section.

        Args:
            **kwargs: IV name=value assignments to determine the child's context. Any IV name not specified here will
               be chosen randomly from the IV's possible values.
        """
        child_context = self.context.new_child()
        child_context[self.next_level] = self.children[-1][self.next_level] + 1
        child_context.update({k: random.choice(v) for k, v in self.next_level_dict.get('ivs', dict()).items()})
        child_context.update(kwargs)
        self.children.append(ExperimentSection(child_context, *self.next_level_inputs))


class Experiment(metaclass=collections.abc.ABCMeta):
    """
    Abstract base class for Experiments.

    Subclass this to create experiments. Experiments should override the run_trial method at minimum and optionally the
    start, end, and inter methods.

    Attributes:
        levels: A list of level names describing the experiment hierarchy.
        ivs_by_level: A mapping of level names to IV name: value dicts, describing which IVs are varied (crossed) at
            each level.
        repeats_by_level: A mapping of level names to integers, describing the number of each unique section type to
            appear at each level.
        sort_by_level: A mapping of level names to sort methods, determining how the sections at each level are sorted.
        output_names: A list of the same length as the number of DVs (outputs of the run_trial method), naming each.
        root: An ExperimentSection instance from which all experiment sections descend.

    Properties:
        data: A pandas DataFrame. Before any sections are run, contains only the IV values of each trial. Afterwards,
           contains both IV and DV values.

    """
    def __init__(self, settings_by_level,
                 levels=('participant', 'session', 'block', 'trial'),
                 experiment_file=None,
                 output_names=None,
                 ):
        """
        Initialize an Experiment instance.

        Args:
            settings_by_level: A mapping of level names to dicts with settings for each level, each mappings with the
                following keys:
                ivs: A mapping of independent variables names to possible values, for the IVs that vary at the
                    associated level.
                sort: The sort method for the level: 'random', indices, or None.
                n: The number of times each unique combination of variables should appear at the associated level.
            levels=('participant', 'session', 'block', 'trial'): The experiment's hierarchy of sections.
            experiment_file=None: A filename where the experiment instance will be pickled, in order to run some
                sections in a later Python session.
            output_names=None: A list of the same length as the number of DVs (outputs of the run_trial method), naming
                each. Will be column labels on the DataFrame in the data property.
        """
        for level in settings_by_level:
            if level not in levels:
                raise KeyError('Unknown level {}.'.format(level))

        self.levels = levels
        self.settings_by_level = settings_by_level
        self.output_names = output_names

        actual_levels = ['root']
        actual_levels.extend(self.levels)
        self.root = ExperimentSection(
            collections.ChainMap(), actual_levels, self.settings_by_level)

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
        """
        Find the experiment section.

        Args:
            kwargs: level=n describing how to descend the hierarchy.

        For example:
            >> first_session = experiment_instance.find_section(participant=1, session=1)

        Returns an ExperimentSection object at the first level where no input kwarg describes how to descend the
            hierarchy.
        """
        node = self.root
        for level in self.levels:
            if level in kwargs:
                logging.debug('Found specified {}.'.format(level))
                node = node.children[kwargs[level]-1]
            else:
                logging.info('No {} specified, returning previous level.'.format(level))
                return node

    def add_section(self, **kwargs):
        """
        Add section to experiment.

        Args:
            kwargs: Same as the input to find_section, describing which section is the parent of the added section.
        """
        find_section_kwargs = {}
        for k in kwargs:
            if k in self.levels:
                find_section_kwargs[k] = kwargs.pop(k)
        self.find_section(**find_section_kwargs).add_child_ad_hoc(**kwargs)

    def run(self, section):
        """
        Run an experiment section.

        Runs a section by descending the hierarchy and running each child section. Also calls the start, end, and inter
        methods where appropriate. Results are saved in the ExperimentSection instances at the lowest level (i.e.,
        trials). Will overwrite any existing results.

        Args:
            section: An ExperimentSection instance to be run.
        """
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