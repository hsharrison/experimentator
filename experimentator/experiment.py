# Copyright (c) 2013-2014 Henry S. Harrison
import os
import sys
import logging
import pickle
import functools
from importlib import import_module
from contextlib import contextmanager
from datetime import datetime
from pandas import DataFrame
from collections import ChainMap

from experimentator.utility import parse_config, QuitSession
from experimentator.section import ExperimentSection


def load_experiment(experiment_file):
    """
    Loads an experiment file. Returns the experiment instance.
    """
    with open(experiment_file, 'rb') as f:
        return pickle.load(f)


def run_experiment_section(experiment, demo=False, section=None, **kwargs):
    """
    Run an experiment instance from a file, and saves it. Monitors for QuitSession exceptions (If a QuitSession
    exception is raised, still saves the data. Running the section again will overwrite it.).

    Args:
      experiment: Filename where an Experiment instance is pickled, or an Experiment instance.
      demo:       If True, don't save data.
      section:    ExperimentSection to run.
      **kwargs:   If section not specified, find section matching kwargs.
    """
    if isinstance(experiment, Experiment):
        exp = experiment
    else:
        exp = load_experiment(experiment)
        exp.experiment_file = experiment

    if not section:
        section = exp.find_section(**kwargs)

    try:
        exp.run_section(section, demo=demo)
    except QuitSession as e:
        logging.warning('Quit event detected: {}.'.format(str(e)))
        # Backup experiment file.
        os.rename(experiment.experiment_file,
                  experiment.experiment_file + datetime.now().strftime('.%m-%d-%H-%M-backup'))
    finally:
        exp.save()


def export_experiment_data(experiment_file, data_file):
    """
    Reads a pickled experiment instance from experiment_file and saves its data in csv format to data_file.
    """
    load_experiment(experiment_file).export_data(data_file)


@contextmanager
def dummy_context():
    yield


class Experiment():
    """
    Abstract base class for Experiments.

    Subclass this to create experiments. Experiments should override the run_trial method at minimum and optionally the
    start, end, and inter methods.

    Attributes:
        settings_by_level: A mapping of level names to dicts with settings for each level, each mappings with the
        following keys:
                           ivs:  A mapping of independent variables names to possible values, for the IVs that vary at
                                 the associated level.
                           sort: The sort method for the level: 'random', indices, or None.
                           n:    The number of times each unique combination of variables should appear at the
                                 associated level.
        levels:            A list of level names describing the experiment hierarchy.
        base_section:              An ExperimentSection instance from which all experiment sections descend.
        data:              A pandas DataFrame. Before any sections are run, contains only the IV values of each trial.
                           Afterwards, contains both IV and DV values.
        experiment_file:   Filename where the experiment is saved to.
        run_callbacks:     A list of functions that are run at the lowest level.
        start_callbacks,
        inter_callbacks,
        end_callbacks:     Dicts of levels mapped to lists of callbacks to be run at the start, between, and after
                           sections of the experiment.
        userdata:          Dict for storing persistent data within an experimental session. Passed to every callback as
                           the first argument. Emptied upon saving the experiment instance.

    Decorator methods:
        run:               Run the decorated function at the lowest level of the experiment (e.g., each trial).
        start:             Run the decorated function at the beginning of each section as a specific level. Input the
                           level name to the decorator.
        inter:             Run the decorated function at between each section as a specific level. Input the level name
                           to the decorator.
        end:               Run the decorated function after each section as a specific level. Input the level name to
                           the decorator.

    """
    def __init__(self, config_file=None,
                 settings_by_level=None,
                 levels=('participant', 'session', 'block', 'trial'),
                 experiment_file=None,
                 ):
        """
        Initialize an Experiment instance.

        Args:
            config_file:          Config filename or ConfigParser object which sets levels and settings_by_level. See
                                  function parse_config for a description of the syntax.
            settings_by_level:    A mapping of level names to dicts with settings for each level, each mappings with the
                                  following keys:
                                  ivs:  A mapping of independent variables names to possible values, for the IVs that
                                        vary at the associated level.
                                  sort: The sort method for the level: 'random', indices, or None.
                                  n:    The number of times each unique combination of variables should appear at the
                                        associated level.
            levels=('participant', 'session', 'block', 'trial'):
                                  The experiment's hierarchy of sections.
            experiment_file=None: A filename where the experiment instance will be pickled, in order to run some
                                  sections in a later Python session.
        """
        if config_file:
            levels, settings_by_level, config_data = parse_config(config_file)
        else:
            config_data = {}

        for level in settings_by_level:
            if level not in levels:
                raise KeyError('Unknown level {}.'.format(level))

        self.levels = levels
        self.settings_by_level = settings_by_level

        actual_levels = ['base_section']
        actual_levels.extend(self.levels)
        self.base_section = ExperimentSection(
            ChainMap(), actual_levels, self.settings_by_level)

        self.run_callbacks = []
        self.start_callbacks = {level: [] for level in actual_levels}
        self.inter_callbacks = {level: [] for level in actual_levels}
        self.end_callbacks = {level: [] for level in actual_levels}

        self.session_data = {'as': {}}
        self.persistent_data = config_data
        self.with_functions = {level: dummy_context for level in actual_levels}

        self.experiment_file = experiment_file
        self.original_module = sys.argv[0][:-3]

    @property
    def data(self):
        data = DataFrame(self.base_section.generate_data()).set_index(list(self.levels))
        return data

    def save(self):
        if self.experiment_file:
            logging.debug('Saving Experiment instance to {}.'.format(self.experiment_file))
            with open(self.experiment_file, 'wb') as f:
                pickle.dump(self, f)

        else:
            logging.warning('Cannot save experiment: No filename provided.')

    def export_data(self, filename):
        with open(filename, 'w') as f:
            self.data.to_csv(f)

    def find_section(self, **kwargs):
        """
        Find the experiment section.

        Args:
            kwargs: level=n describing how to descend the hierarchy (uses one-based indexing).

        For example:
            >> first_session = experiment_instance.find_section(participant=1, session=1)

        Returns an ExperimentSection object at the first level where no input kwarg describes how to descend the
        hierarchy.
        """
        node = self.base_section
        for level in self.levels:
            if level in kwargs:
                logging.debug('Found specified {}.'.format(level))
                node = node.children[kwargs[level]-1]
            else:
                logging.info('No {} specified, returning previous level.'.format(level))
                break

        return node

    def find_first_not_run(self, at_level, by_started=True):
        """
        Search through all sections at the specified level, and return the first not already run. If by_started=True, a
        section is considered already run if it has started. Otherwise, it is considered already run only if it has
        finished.
        """
        attribute = {True: 'has_started', False: 'has_finished'}[by_started]
        node = self.base_section
        section = {}
        for level in self.levels:
            logging.debug('Checking all {}s...'.format(level))
            found = False
            for i, child in enumerate(node.children):
                if not getattr(child, attribute):
                    node = child
                    section[level] = i+1
                    found = True
                    break

            if level == at_level:
                break

        if found:
            return self.find_section(**section)
        else:
            logging.warning('Could not find a {} not run.'.format(at_level))
            return None

    def add_section(self, **kwargs):
        """
        Add section to experiment.

        Args:
            kwargs: Same as the input to find_section, describing which section is the parent of the added section.
                    Any other kwargs are passed onto add_child_ad_hoc as section settings.
        """
        find_section_kwargs = {}
        for k in kwargs:
            if k in self.levels:
                find_section_kwargs[k] = kwargs.pop(k)
        self.find_section(**find_section_kwargs).add_child_ad_hoc(**kwargs)

    def run_section(self, section, demo=False):
        """
        Run an experiment section.

        Runs a section by descending the hierarchy and running each child section. Also calls the start, end, and inter
        methods where appropriate. Results are saved in the ExperimentSection instances at the lowest level (i.e.,
        trials). Will overwrite any existing results.

        Args:
            section:    An ExperimentSection instance to be run.
            demo=False: If demo, don't save data.
        """
        logging.debug('Running {} with context {}.'.format(section.level, section.context))

        with self.with_functions[section.level]() as self.session_data['as'][section.level]:

            if not demo:
                section.has_started = True

            if section.is_bottom_level:
                results = {}
                for func in self.run_callbacks:
                    results.update(func(self.session_data, self.persistent_data, **section.context))
                logging.debug('Results: {}.'.format(results))

                if not demo:
                    section.add_data(**results)
                    logging.debug('New context: {}.'.format(section.context))

            else:
                for func in self.start_callbacks[section.level]:
                    func(self.session_data, self.persistent_data, **section.context)

                for i, next_section in enumerate(section.children):
                    if i:  # don't run inter on first section of level
                        for func in self.inter_callbacks[section.next_level]:
                            func(self.session_data, self.persistent_data, **next_section.context)

                    self.run_section(next_section)

                for func in self.end_callbacks[section.level]:
                    func(self.session_data, self.persistent_data, **section.context)

        if not demo:
            section.has_finished = True

    def set_with_function(self, level, func, *args, **kwargs):
        self.with_functions[level] = functools.partial(func, *args, **kwargs)

    def __getstate__(self):
        state = self.__dict__.copy()
        #  Clear session_data before pickling.
        state['session_data'] = {'as': {}}
        # Save only function names.
        state['run_callbacks'] = _dereference_functions(state['run_callbacks'])
        for level in state['levels']:
            for callback in ('start_callbacks', 'inter_callbacks', 'end_callbacks'):
                state[callback][level] = _dereference_functions(state[callback][level])
        return state

    def __setstate__(self, state):
        # Import original module.
        try:
            original_module = import_module(state['original_module'])
        except ImportError:
            logging.warning("The original script that created this experiment doesn't seem to be in this directory.")
            raise
        # Replace references to callbacks functions.
        state['run_callbacks'] = _rereference_functions(original_module, state['run_callbacks'])
        for level in state['levels']:
            for callback in ('start_callbacks', 'inter_callbacks', 'end_callbacks'):
                state[callback][level] = _rereference_functions(original_module, state[callback][level])
        self.__dict__.update(state)

    # Decorators
    def run(self, func):
        """
        Decorate a function with this to run that function at each trial.
        """
        self.run_callbacks.append(func)
        return func

    def start(self, level):
        """
        Decorate a function with this to run it at the start of a section. Pass the level name as an input to the
        decorator.
        """
        def start_decorator(func):
            self.start_callbacks[level].append(func)
            return func
        return start_decorator

    def inter(self, level):
        """
        Decorate a function with this to run it at between sections. Pass the level name as an input to the decorator.
        """
        def inter_decorator(func):
            self.inter_callbacks[level].append(func)
            return func
        return inter_decorator

    def end(self, level):
        """
        Decorate a function with this to run it at after each section. Pass the level name as an input to the decorator.
        """
        def end_decorator(func):
            self.end_callbacks[level].append(func)
            return func
        return end_decorator


def _dereference_functions(funcs):
    return [func.__name__ for func in funcs]


def _rereference_functions(module, func_names):
    return [getattr(module, func) for func in func_names]
