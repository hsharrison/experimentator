# Copyright (c) 2013-2014 Henry S. Harrison
import os
import sys
import logging
import pickle
import functools
from importlib import import_module
from contextlib import contextmanager
from datetime import datetime
from collections import ChainMap

from experimentator.common import QuitSession
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
        section = exp.section(**kwargs)

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


class Experiment():
    def __init__(self, tree, experiment_file=None):
        self.tree = tree
        self.experiment_file = experiment_file
        self.levels = list(zip(*self.tree.levels_and_designs))[0]

        self.tree.add_base_level()
        self.base_section = ExperimentSection(ChainMap(), self.tree)

        self.run_callback = _dummy_callback
        callbacks = {level: _dummy_callback for level in self.levels}
        callbacks.update({'base': _dummy_callback})
        self.start_callbacks = callbacks.copy()
        self.inter_callbacks = callbacks.copy()
        self.end_callbacks = callbacks.copy()

        self.session_data = {'as': {}}
        self.persistent_data = {}
        self.context_managers = {level: _dummy_context for level in self.levels}
        self.context_managers.update({'base': _dummy_context})

        self.original_module = sys.argv[0][:-3]

    @property
    def data(self):
        from pandas import DataFrame
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

    def section(self, **kwargs):
        """
        Return an experiment section.

        Args:
            kwargs: level=n describing how to descend the hierarchy (uses one-based indexing).

        For example:
            >> first_session = experiment_instance.section(participant=1, session=1)

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
            return self.section(**section)
        else:
            logging.warning('Could not find a {} not run.'.format(at_level))
            return None

    def add_section(self, **kwargs):
        """
        Add section to experiment.

        Args:
            kwargs: Same as the input to section, describing which section is the parent of the added section.
                    Any other kwargs are passed onto add_child_ad_hoc as section settings.
        """
        find_section_kwargs = {}
        for k in kwargs:
            if k in self.levels:
                find_section_kwargs[k] = kwargs.pop(k)
        self.section(**find_section_kwargs).add_child_ad_hoc(**kwargs)

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

        # Enter context.
        with self.context_managers[section.level]() as self.session_data['as'][section.level]:

            if not demo:
                section.has_started = True

            if section.is_bottom_level:
                # Run a trial (or whatever the lowest level is.
                results = self.run_callback(self.session_data, self.persistent_data, **section.context)
                logging.debug('Results: {}.'.format(results))

                if not demo:
                    # Save the data
                    section.add_data(**results)
                    logging.debug('New context: {}.'.format(section.context))

            else:
                self.start_callbacks[section.level](self.session_data, self.persistent_data, **section.context)

                for i, next_section in enumerate(section.children):
                    if i:  # don't run inter on first section of level
                        self.inter_callbacks[section.level](self.session_data, self.persistent_data, **section.context)
                    self.run_section(next_section)

                self.end_callbacks[section.level](self.session_data, self.persistent_data, **section.context)

        if not demo:
            section.has_finished = True

    def set_contextmanager(self, level, func, *args, **kwargs):
        self.context_managers[level] = functools.partial(func, *args, **kwargs)

    def __getstate__(self):
        state = self.__dict__.copy()
        #  Clear session_data before pickling.
        state['session_data'] = {'as': {}}
        # Save only function names.
        state['run_callbacks'] = state['run_callbacks'].__name__
        for level in state['levels']:
            for callback in ('start_callbacks', 'inter_callbacks', 'end_callbacks'):
                state[callback][level] = state[callback][level].__name__
        return state

    def __setstate__(self, state):
        # Import original module.
        try:
            original_module = import_module(state['original_module'])
        except ImportError:
            logging.warning("The original script that created this experiment doesn't seem to be in this directory.")
            raise
        # Replace references to callbacks functions.
        state['run_callback'] = getattr(original_module, state['run_callback'])
        for level in state['levels']:
            for callback in ('start_callbacks', 'inter_callbacks', 'end_callbacks'):
                state[callback][level] = getattr(original_module, state[callback][level])
        self.__dict__.update(state)

    def set_run_callback(self, func):
        self.run_callback = func

    def set_start_callback(self, level, func):
        self.start_callbacks[level] = func

    def set_inter_callback(self, level, func):
        self.inter_callbacks[level] = func

    def set_end_callback(self, level, func):
        self.end_callbacks[level] = func


@contextmanager
def _dummy_context():
    yield


def _dummy_callback(*args, **kwargs):
    return {}
