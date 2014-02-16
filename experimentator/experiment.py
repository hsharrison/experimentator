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
from contextlib import contextmanager, ExitStack
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


def run_experiment_section(experiment, demo=False, parent_callbacks=True, section=None, from_section=1,
                           **section_numbers):
    """Run an experiment section.

    Runs an experiment instance from a file or an `Experiment` instance, and saves it. If a `QuitSession` exception is
    encountered, the `Experiment` will be backed up and saved before exiting the session.

    Arguments
    ---------
    experiment : str or Experiment
        File location where an `Experiment` instance is pickled, or an Experiment instance.
    demo : bool, optional
        If True, data will not be saved and sections will not be marked as run.
    parent_callbacks : bool, optional
            If True (the default), all parent callbacks will be called.
    section : ExperimentSection, optional
        The section of the experiment to run. Alternatively, the section can be specified in the keyword arguments.
    from_section : int or list of int, optional
            Which section to start running from. This makes it possible to resume a session. If a list is passed, it
            specifies where to start running on multiple levels. For example:

            >>> run_experiment_section(exp, participant=1, session=2, from_section=[3, 5])

            Assuming the hierarchy is ``('participant', 'session', 'block', 'trial')``, this would run the first
            participant's second session, starting from the fifth trial of the third block.
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
        exp.run_section(section, demo=demo, parent_callbacks=parent_callbacks)
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
        callbacks.update({'_base': _dummy_callback})
        self.start_callbacks = callbacks.copy()
        self.inter_callbacks = callbacks.copy()
        self.end_callbacks = callbacks.copy()

        args = {level: (None, None) for level in self.levels}
        args.update({'_base': (None, None)})
        self._run_callback_args = (None, None)
        self._start_callback_args = args.copy()
        self._inter_callback_args = args.copy()
        self._end_callback_args = args.copy()

        self.session_data = {'as': {}}
        self.persistent_data = {}
        self.context_managers = {level: _dummy_context for level in self.levels}
        self.context_managers.update({'_base': _dummy_context})
        self._context_manager_args = args.copy()

        self.original_module = sys.argv[0][:-3]

    def __repr__(self):
        return 'Experiment({}, experiment_file={})'.format(self.tree.__repr__(), self.experiment_file)

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
                logger.info('No {} specified, returning to previous level.'.format(level))
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

        if section.tree[1][0] in section_numbers:
            # Remove the section from section_numbers...it needs to be empty to signal completion.
            numbers = section_numbers.pop(section.tree[1][0])

            if isinstance(numbers, int):  # Only one number specified.
                if section_numbers:  # We're not done.
                    yield from self.all_sections(_section=section[numbers-1], **section_numbers)
                else:  # We're done.
                    yield section[numbers-1]

            else:  # Multiple numbers specified.
                if section_numbers:  # We're not done.
                    for n in numbers:
                        yield from self.all_sections(_section=section[n-1], **section_numbers)
                else:  # We're done.
                    yield from (section[n-1] for n in numbers)
        else:
            # Section not specified but we're not done; descend into every child.
            for child in section.children:
                yield from self.all_sections(_section=child, **section_numbers)

    def find_first_not_run(self, at_level, by_started=True, starting_at=None):
        """Find the first section that has not been run.

        Searches the experimental hierarchy, returning the first `ExperimentSection` at `level` that has not been run.

        Arguments
        ---------
        at_level : str
            Which level to search.
        by_started : bool, optional
            If true (default), finds the first section that has not been started. Otherwise, finds the first section
            that has not finished.
        starting_at : ExperimentSection, optional
            Starts the search at the given `ExperimentSection`. Allows for finding the first section not run of a
            particular part of the experiment. For example, the first block not run of the second participant could be
            found by:

            >>> exp.find_first_not_run('block', starting_at=exp.section(participant=2))

        Returns
        -------
        ExperimentSection
            The first `ExperimentSection` satisfying the specified criteria.

        """
        if by_started:
            key = lambda x: not x.has_started
            descriptor = 'not started'
        else:
            key = lambda x: not x.has_finished
            descriptor = 'not finished'

        return self._find_top_down(at_level, key, starting_at=starting_at, descriptor=descriptor)

    def find_first_partially_run(self, at_level, starting_at=None):
        """Find the first section that has been partially run.

        Searches the experimental hierarchy, returning the first `ExperimentSection` at `level` that has been started
        but not finished.

        Arguments
        ---------
        at_level : str
            Which level to search.
        starting_at : ExperimentSection, optional
            Starts the search at the given `ExperimentSection`. Allows for finding the first partially-run section of a
            particular part of the experiment.

        Returns
        -------
        ExperimentSection
            The first `ExperimentSection` satisfying the specified criteria.

        """
        return self._find_top_down(at_level, lambda x: x.has_started and not x.has_finished,
                                   starting_at=starting_at, descriptor='partially run')

    def _find_top_down(self, at_level, key, starting_at=None, descriptor=''):
        node = starting_at or self.base_section
        while not node.level == at_level:
            level = node.tree[1][0]
            logger.debug('Checking all {}s...'.format(level))
            next_node = None
            for child in node:
                if key(child):
                    next_node = child
                    break

            if not next_node:
                logger.warning('Count not find a {} {}'.format(level, descriptor))
                return
            node = next_node

        return node

    def run_section(self, section, demo=False, parent_callbacks=True, from_section=None):
        """Run a section.

        Runs a section by descending the hierarchy and running each child section. Also calls the start, end, and inter
        callbacks where appropriate. Results are saved in each `ExperimentSection.context` attribute.

        Arguments
        ---------
        section : ExperimentSection
            The `ExperimentSection` instance to be run.
        demo : bool, optional
            Data will only be saved if `demo` is False (the default).
        parent_callbacks : bool, optional
            If True (the default), all parent callbacks will be called.
        from_section : int or list of int, optional
            Which section to start running from. This makes it possible to resume a session. If a list is passed, it
            specifies where to start running on multiple levels. For example:

            >>> exp.run_section(exp.section(participant=1, session=2), from_section=[3, 5])

            Assuming the hierarchy is ``('participant', 'session', 'block', 'trial')``, this would run the first
            participant's second session, starting from the fifth trial of the third block.

        """
        logger.debug('Running {} with context {}.'.format(section.level, section.context))

        if isinstance(from_section, int):
            from_section = [from_section]
        if from_section is None:
            from_section = [1]
        if len(from_section) > 1:
            next_from_section = from_section[1:]
        else:
            next_from_section = [1]

        # Handle parent callbacks and set parent has_started to True.
        with ExitStack() as stack:
            if parent_callbacks:
                logger.debug('Entering all parent levels...')
            for parent in self.parents(section):
                parent.has_started = True
                if parent_callbacks:
                    logger.debug('Entering {} with context {}...'.format(parent.level, parent.context))
                    stack.enter_context(self._enter_level(
                        parent.level, self.session_data, self.persistent_data, _call_inter=False, **parent.context))

            # Back to the regular behavior.
            with self._enter_level(section.level, self.session_data, self.persistent_data, **section.context) as \
                    self.session_data['as'][section.level]:

                if not demo:
                    section.has_started = True

                if section.is_bottom_level:
                    results = self.run_callback(self.session_data, self.persistent_data, **section.context)
                    logger.debug('Results: {}.'.format(results))

                    if not demo:
                        section.add_data(**results)

                else:  # Not bottom level.
                    for next_section in section[from_section[0]-1:]:
                        self.run_section(
                            next_section, demo=demo, parent_callbacks=False, from_section=next_from_section)

            if not demo:
                section.has_finished = True

            if parent_callbacks:
                logger.debug('Exiting all parent levels...')

        # Finished parents detection.
        if not section.level == '_base':
            for parent in reversed(list(self.parents(section))):
                if all(child.has_finished for child in parent):
                    parent.has_finished = True

    def resume_section(self, section, **kwargs):
        """Resume a section.

        Reruns a section that has been started but not finished, starting where running left off.

        Arguments
        ---------
        section : ExperimentSection
            The section to resume.
        **kwargs
            Arbitrary keyword arguments to pass to `Experiment.run_section`. See its docstring for details.

        """
        if section.is_bottom_level:
            raise ValueError('Cannot resume a section at the lowest level')
        if not section.has_started:
            raise ValueError('Cannot resume a section that has not started')
        if section.has_finished:
            raise ValueError('Cannot resume a section that has finished')

        levels, _ = zip(*section.tree)

        start_at_numbers = []
        start_at_section = section
        for level in levels[1:]:
            start_at_section = self.find_first_not_run(level, starting_at=start_at_section)
            start_at_numbers.append(start_at_section.context[level])

        self.run_section(section, from_section=start_at_numbers, **kwargs)

    def parents(self, section):
        """Find parents.

        Returns a list of all parents of a section, in top-to-bottom order.

        Arguments
        ---------
        section : ExperimentSection
            The section to find the parents of.

        Yields
        -------
        ExperimentSection
            Sections, one per level, each a parent of the next, and the last a parent of `section`.

        """
        parent_section_numbers = {}
        for level in self.levels:
            if level == section.level or section.level == '_base':
                break

            parent_section_numbers.update({level: section.context[level]})
            yield self.section(**parent_section_numbers)

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
                if not (state[callback][level] == _dummy_callback or state[callback][level] == _dummy_context):
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
                if isinstance(state[callback][level], str):
                    state[callback][level] = functools.partial(getattr(original_module, state[callback][level]),
                                                               *args[0], **args[1])
        self.__dict__.update(state)

    @contextmanager
    def _enter_level(self, level, *args, _call_inter=True, **kwargs):
        if _call_inter and not level == '_base' and kwargs.get(level) > 1:
            self.inter_callbacks[level](*args, **kwargs)

        self.start_callbacks[level](*args, **kwargs)

        with self.context_managers[level](*args, **kwargs) as context_manager_output:
            yield context_manager_output

        self.end_callbacks[level](*args, **kwargs)


@contextmanager
def _dummy_context(*args, **kwargs):
    yield


def _dummy_callback(*args, **kwargs):
    return {}
