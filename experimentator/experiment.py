"""Experiment module.

This module contains the `Experiment` class and associated helper functions. This is a private module, its public
objects are imported in `__init__.py`.

"""
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

logger = logging.getLogger(__name__)


def load_experiment(experiment_file):
    """Load an experiment from disk.

    Arguments
    ---------
    experiment_file : str
        File location containing a pickled `Experiment` instance.

    Returns
    -------
    Experiment
        The pickled `Experiment`.

    """
    with open(experiment_file, 'rb') as f:
        return pickle.load(f)


def run_experiment_section(experiment, demo=False, section=None, **section_numbers):
    """Run an experiment section.

    Runs an experiment instance from a file or an `Experiment` instance, and saves it. If a `QuitSession` exception is
    encountered, the `Experiment` will be backed up and saved before exiting the session.

    Arguments
    ---------
    experiment : str or Experiment
        File location where an `Experiment` instance is pickled, or an Experiment instance.
    demo : bool, optional
        If True, data will not be saved and sections will not be marked as run.
    section : ExperimentSection, optional
        The section of the experiment to run. Alternatively, the section can be specified in the keyword arguments.
    **section_numbers
        Keyword arguments describing how to descend the experiment hierarchy to find a section to be run. For example,
        `run_experiment_section(..., participant=3, session=1)` to run the third participant's first session (section
        numbers are indexed by 1s).

    """
    if isinstance(experiment, Experiment):
        exp = experiment
    else:
        exp = load_experiment(experiment)
        exp.experiment_file = experiment

    if not section:
        section = exp.section(**section_numbers)

    try:
        exp.run_section(section, demo=demo)
    except QuitSession as e:
        logger.warning('Quit event detected: {}.'.format(str(e)))
        # Backup experiment file.
        os.rename(experiment.experiment_file,
                  experiment.experiment_file + datetime.now().strftime('.%m-%d-%H-%M-backup'))
    finally:
        exp.save()


def export_experiment_data(experiment_file, data_file):
    """ Export data.

    Reads a pickled experiment instance and saves its data in `.csv` format.

    Arguments
    ---------
    experiment_file : str
        The file location where an `Experiment` instance is pickled.
    data_file : str
        The file location where the data will be written.

    Note
    ----
    This shortcut function is not recommended for experiments with compound data types, for example an experiment which
    stores a time series for every trial. In those cases it is recommended to write a custom script that parses the
    `Experiment.data` attribute as desired.

    """
    load_experiment(experiment_file).export_data(data_file)


class Experiment():
    """Experiment.

    An `Experiment` instance handles all aspects of an experiment. It contains the entire experimental hierarchy and
    stores the data. It is picklable, to facilitate running an experiment over multiple Python sessions.

    Arguments
    ---------
    tree : DesignTree
        A `DesignTree` instance defining the experiment hierarchy.
    experiment_file : str, optional
        A file location where the `Experiment` will be pickled.

    Attributes
    ----------
    data
    tree : DesignTree
        The `DesignTree` instance defining the experiment's hierarchy.
    experiment_file : str
        The file location where the `Experiment` will be pickled.
    levels : list of str
        The levels of the experiment, as defined in `Experiment.tree`.
    base_section : ExperimentSection
        The root of the experiment hierarchy; an `ExperimentSection` instance from which all other `ExperimentSection`s
        descend.
    run_callback : func
        The function to be run when the bottom of the tree is reached (i.e., the trial function).
    start_callbacks, inter_callbacks, end_callbacks : dict
        Dictionaries, with keys naming levels and values as functions to be run at the beginning, in-between, and after
        running `ExperimentSection`\ s at the associated level.
    context_managers : dict
        A dictionary, with level names as keys and context manager functions as values. An alternative way to define
        behavior to run at the start and end of `ExperimentSection`\ s.
    session_data : dict
        A dictionary where data can be stored that is persistent between `ExperimentSection`\ s run in the same Python
        session. This is the first positional argument for every callback, and a good place to store external resources
        that aren't picklable but can be loaded in a start callback. Anything yielded by a context manager will be saved
        here, in `session_data['as'][level]`. Note that this dictionary is emptied before pickling the `Experiment`.
    persistent_data : dict
        A dictionary where data can be stored that is persistent across Python sessions. Everything here must be
        picklable.
    original_module : str
        The filename which originally created this `Experiment`. This is where the `Experiment` will look for its
        callbacks when it is loaded from disk.

    """
    def __init__(self, tree, experiment_file=None):
        self.tree = tree
        self.experiment_file = experiment_file
        self.levels = list(zip(*self.tree.levels_and_designs))[0]

        self.tree.add_base_level()
        self.base_section = ExperimentSection(self.tree, ChainMap())

        self.run_callback = _dummy_callback
        callbacks = {level: _dummy_callback for level in self.levels}
        callbacks.update({'base': _dummy_callback})
        self.start_callbacks = callbacks.copy()
        self.inter_callbacks = callbacks.copy()
        self.end_callbacks = callbacks.copy()

        args = {level: (None, None) for level in self.levels}
        args.update({'base': (None, None)})
        self._run_callback_args = (None, None)
        self._start_callback_args = args.copy()
        self._inter_callback_args = args.copy()
        self._end_callback_args = args.copy()

        self.session_data = {'as': {}}
        self.persistent_data = {}
        self.context_managers = {level: _dummy_context for level in self.levels}
        self.context_managers.update({'base': _dummy_context})
        self._context_manager_args = args.copy()

        self.original_module = sys.argv[0][:-3]

    @property
    def data(self):
        """Data.

        Returns
        -------
        pandas.DataFrame
            A `DataFrame` containing all of the `Experiment`'s data. The `DataFrame` will be MultiIndexed, with section
            numbers as indexes. Independent variables will also be included as columns.

        """
        from pandas import DataFrame
        data = DataFrame(self.base_section.generate_data()).set_index(list(self.levels))
        return data

    def save(self):
        """Save experiment.

        Pickles the `Experiment` to the location in `Experiment.experiment_file`.

        """
        if self.experiment_file:
            logger.debug('Saving Experiment instance to {}.'.format(self.experiment_file))
            with open(self.experiment_file, 'wb') as f:
                pickle.dump(self, f)

        else:
            logger.warning('Cannot save experiment: No filename provided.')

    def export_data(self, filename):
        """Export data.

        Exports `Experiment.data` in `.csv` format.

        Arguments
        ---------
        filename : str
            A file location where the data should be saved.

        Note
        ----
        This method is not recommended for experiments with compound data types, for example an experiment
        which stores a time series for every trial. In those cases it is recommended to write a custom script that
        parses the `Experiment.data` attribute as desired.

        """
        with open(filename, 'w') as f:
            self.data.to_csv(f)

    def section(self, **section_numbers):
        """Find single section by number.

        Finds an `ExperimentSection` based on section numbers.

        Arguments
        ---------
        **section_numbers
            Keyword arguments describing which section to find. Must include every level higher than the desired
            section. This method will descend the experimental hierarchy until it can no longer determine how to
            proceed, at which point it returns the current `ExperimentSection`.

        Returns
        -------
        ExperimentSection
            The specified section.

        See Also
        --------
        Experiment.all_sections : find all sections matching a set of criteria

        Examples
        --------
        Assuming an `Experiment` named ``exp`` with levels ``['participant', 'session', 'block', 'trial']``:

        >>>some_block = exp.section(participant=2, session=1, block=3)

        """
        node = self.base_section
        for level in self.levels:
            if level in section_numbers:
                logger.debug('Found specified {}.'.format(level))
                node = node.children[section_numbers[level]-1]
            else:
                logger.info('No {} specified, returning previous level.'.format(level))
                break

        return node

    def all_sections(self, **section_numbers):
        """Find a set of sections by number.

        Finds all sections in the experiment matching the given section numbers.

        Arguments
        ---------
        **section_numbers
            Keyword arguments describing what sections to find. Keys are level names, values are ints or sequences of
            ints.

        Yields
        ------
        ExperimentSection
            The specified `ExperimentSection` instances. The returned sections will be at the lowest level given in
            `section_numbers`. When encountering levels that aren't in `section_numbers` before reaching its lowest
            level, all sections will be descended into.

        See Also
        --------
        Experiment.section : find a single section.

        Examples
        --------
        Assuming an `Experiment` named ``exp`` with levels ``['participant', 'session', 'block', 'trial']``:

        >>>all_first_sessions = exp.all_sections(session=1)

        ``all_first_sessions`` will be the first session of every participant.

        >>>trials = exp.all_sections(block=1, trial=2)

        ``trials`` will be the second trial of the first block in every session.

        >>>other_trials = exp.all_sections(session=1, trial=[1, 2, 3])

        ``other_trials`` will be the first three trials of every block in the first session of every participant.

        """
        # The state of the recursion is passed in the keyword argument '_section'.
        section = section_numbers.pop('_section', self.base_section)

        if section.is_bottom_level or not section_numbers:
            # When section_numbers is empty, we're done with the search.
            yield section

        elif section.level in section_numbers:
            # Remove the section from section_numbers...it needs to be empty to signal completion.
            numbers = section_numbers.pop(section.level)
            yield from (self.all_sections(_section=section.children[n-1]) for n in numbers)

        else:
            # Section not specified but we're not done; descend into every child.
            yield from (self.all_sections(_section=child) for child in section.children)

    def find_first_not_run(self, at_level, by_started=True):
        """Find the first section that has not been run.

        Searches the experimental hierarchy, returning the first `ExperimentSection` at a given level that has not been
        run.

        Arguments
        ---------
        at_level : str
            Which level to search.
        by_started : bool, optional
            If true (default), finds the first section that has not been started. Otherwise, finds the first section
            that has not finished.

        Returns
        -------
        ExperimentSection
            The first `ExperimentSection` satisfying the specified criteria.

        """
        attribute = 'has_started' if by_started else 'has_finished'
        node = self.base_section
        section = {}
        for level in self.levels:
            logger.debug('Checking all {}s...'.format(level))
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
            logger.warning('Could not find a {} not run.'.format(at_level))
            return None

    def run_section(self, section, demo=False):
        """Run a section.

        Runs a section by descending the hierarchy and running each child section. Also calls the start, end, and inter
        callbacks where appropriate. Results are saved in each `ExperimentSection.context` attribute.

        Arguments
        ---------
        section : ExperimentSection
            The `ExperimentSection` instance to be run.
        demo : bool, optional
            Data will only be saved if `demo` is False (the default).

        """
        logger.debug('Running {} with context {}.'.format(section.level, section.context))

        # Enter context.
        with self.context_managers[section.level]() as self.session_data['as'][section.level]:

            if not demo:
                section.has_started = True

            if section.is_bottom_level:
                # Run a trial (or whatever the lowest level is.
                results = self.run_callback(self.session_data, self.persistent_data, **section.context)
                logger.debug('Results: {}.'.format(results))

                if not demo:
                    # Save the data
                    section.add_data(**results)
                    logger.debug('New context: {}.'.format(section.context))

            else:
                self.start_callbacks[section.level](self.session_data, self.persistent_data, **section.context)

                for i, next_section in enumerate(section.children):
                    if i:  # don't run inter on first section of level
                        self.inter_callbacks[section.level](self.session_data, self.persistent_data, **section.context)
                    self.run_section(next_section)

                self.end_callbacks[section.level](self.session_data, self.persistent_data, **section.context)

        if not demo:
            section.has_finished = True

    def set_context_manager(self, level, func, *args, **kwargs):
        """Set a context manager to run at a certain level.

        Defines a context manager to run at every section at a particular level. This is an alternative to start and end
        callbacks, to define behavior to occur at the beginning and end of every section. See :mod:`contextlib` for
        details on building context managers.

        Arguments
        ---------
        level : str
            Which level of the hierarchy to manage.
        func : func
            The context manager function.
        *args
            Any arbitrary positional arguments to be passed to `func`.
        **kwargs
            Any arbitrary keyword arguments to be passed to `func`.

        Note
        ----
        In addition to the arguments you set in `*args` and `**kwargs`, two positional arguments will be passed to
        `func`: `Experiment.session_data` and `Experiment.persistent_data`. Additionally, the items in the dictionary in
        the section's `ExperimentSection.context` attribute will be passed as keyword arguments. So the context manager
        should take the form of `(*args, session_data, persistent_data, **kwargs, **context)`, where `*args` and
        `**kwargs` come from this function, `session_data` and `persistent_data` come from the `Experiment` instance,
        and `context` comes from the `ExperimentSection` instance. Since the context can have many items, it is best
        practice to use the keyword argument wildcard `**` in your definition of `func`.

        """
        self.context_managers[level] = functools.partial(func, *args, **kwargs)
        self._context_manager_args[level] = (args, kwargs)

    def set_run_callback(self, func, *args, **kwargs):
        """Set the run callback.

        Define a function to run at the lowest level of the experiment (i.e., the trial function).

        Arguments
        ---------
        func : func
            The function to be set as the run callback.
        *args
            Any arbitrary positional arguments to be passed to `func`.
        **kwargs
            Any arbitrary keyword arguments to be passed to `func`.

        Note
        ----
        In addition to the arguments you set in `*args` and `**kwargs`, two positional arguments will be passed to
        `func`: `Experiment.session_data` and `Experiment.persistent_data`. Additionally, the items in the dictionary in
        the section's `ExperimentSection.context` attribute will be passed as keyword arguments. So the run callback
        should take the form of `(*args, session_data, persistent_data, **kwargs, **context)`, where `*args` and
        `**kwargs` come from this function, `session_data` and `persistent_data` come from the `Experiment` instance,
        and `context` comes from the `ExperimentSection` instance. Since the context can have many items, it is best
        practice to use the keyword argument wildcard `**` in your definition of `func`.

        """
        self.run_callback = functools.partial(func, *args, **kwargs)
        self._run_callback_args = (args, kwargs)

    def set_start_callback(self, level, func, *args, **kwargs):
        """Set a start callback.

        Define a function to run at the at the beginning of every section at a particular level.

        Arguments
        ---------
        level : str
            The level of the hierarchy at which the callback should be set.
        func : func
            The function to be set as the callback.
        *args
            Any arbitrary positional arguments to be passed to `func`.
        **kwargs
            Any arbitrary keyword arguments to be passed to `func`.

        Note
        ----
        In addition to the arguments you set in `*args` and `**kwargs`, two positional arguments will be passed to
        `func`: `Experiment.session_data` and `Experiment.persistent_data`. Additionally, the items in the dictionary in
        the section's `ExperimentSection.context` attribute will be passed as keyword arguments. So the start callback
        should take the form of `(*args, session_data, persistent_data, **kwargs, **context)`, where `*args` and
        `**kwargs` come from this function, `session_data` and `persistent_data` come from the `Experiment` instance,
        and `context` comes from the `ExperimentSection` instance. Since the context can have many items, it is best
        practice to use the keyword argument wildcard `**` in your definition of `func`.

        """
        self.start_callbacks[level] = functools.partial(func, *args, **kwargs)
        self._start_callback_args[level] = (args, kwargs)

    def set_inter_callback(self, level, func, *args, **kwargs):
        """Set a start callback.

        Define a function to run in-between sections at a particular level.

        Arguments
        ---------
        level : str
            The level of the hierarchy at which the callback should be set.
        func : func
            The function to be set as the callback.
        *args
            Any arbitrary positional arguments to be passed to `func`.
        **kwargs
            Any arbitrary keyword arguments to be passed to `func`.

        Note
        ----
        In addition to the arguments you set in `*args` and `**kwargs`, two positional arguments will be passed to
        `func`: `Experiment.session_data` and `Experiment.persistent_data`. Additionally, the items in the dictionary in
        the section's `ExperimentSection.context` attribute will be passed as keyword arguments. So the inter callback
        should take the form of `(*args, session_data, persistent_data, **kwargs, **context)`, where `*args` and
        `**kwargs` come from this function, `session_data` and `persistent_data` come from the `Experiment` instance,
        and `context` comes from the `ExperimentSection` instance. Since the context can have many items, it is best
        practice to use the keyword argument wildcard `**` in your definition of `func`. Note that the context passed
        to the inter callback is that of the next `ExperimentSection`.

        """
        self.inter_callbacks[level] = functools.partial(func, *args, **kwargs)
        self._inter_callback_args[level] = (args, kwargs)

    def set_end_callback(self, level, func, *args, **kwargs):
        """Set an end callback.

        Define a function to run at the at the end of every section at a particular level.

        Arguments
        ---------
        level : str
            The level of the hierarchy at which the callback should be set.
        func : func
            The function to be set as the callback.
        *args
            Any arbitrary positional arguments to be passed to `func`.
        **kwargs
            Any arbitrary keyword arguments to be passed to `func`.

        Note
        ----
        In addition to the arguments you set in `*args` and `**kwargs`, two positional arguments will be passed to
        `func`: `Experiment.session_data` and `Experiment.persistent_data`. Additionally, the items in the dictionary in
        the section's `ExperimentSection.context` attribute will be passed as keyword arguments. So the end callback
        should take the form of `(*args, session_data, persistent_data, **kwargs, **context)`, where `*args` and
        `**kwargs` come from this function, `session_data` and `persistent_data` come from the `Experiment` instance,
        and `context` comes from the `ExperimentSection` instance. Since the context can have many items, it is best
        practice to use the keyword argument wildcard `**` in your definition of `func`.

        """
        self.end_callbacks[level] = functools.partial(func, *args, **kwargs)
        self._end_callback_args[level] = (args, kwargs)

    def __getstate__(self):
        state = self.__dict__.copy()
        #  Clear session_data before pickling.
        state['session_data'] = {'as': {}}

        # Save only function names.
        state['run_callbacks'] = state['run_callbacks'].__name__
        for level in state['levels']:
            for callback in ('start_callbacks', 'inter_callbacks', 'end_callbacks', 'context_managers'):
                state[callback][level] = state[callback][level].__name__
        return state

    def __setstate__(self, state):
        # Import original module.
        try:
            original_module = import_module(state['original_module'])
        except ImportError:
            logger.warning("The original script that created this experiment doesn't seem to be in this directory.")
            raise

        # Replace references to callbacks functions.
        state['run_callback'] = functools.partial(getattr(original_module, state['run_callback']),
                                                  *state['_run_callback_args'][0], **state['_run_callback_args'][1])
        for level in state['levels']:
            for callback, args in (('start_callbacks', '_start_callback_args'),
                                   ('inter_callbacks', '_inter_callback_args'),
                                   ('end_callbacks', '_end_callback_args'),
                                   ('context_managers', '_context_manager_args')):
                state[callback][level] = functools.partial(getattr(original_module, state[callback][level]),
                                                           *args[0], **args[1])
        self.__dict__.update(state)


@contextmanager
def _dummy_context():
    yield


def _dummy_callback(*args, **kwargs):
    return {}
