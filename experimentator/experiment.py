"""Experiment module.

This module contains the `Experiment` class and associated helper functions. This is a private module, its public
objects are imported in `__init__.py`.

"""
import os
import pickle
import inspect
import functools
from logging import getLogger
from importlib import import_module
from contextlib import contextmanager, ExitStack
from datetime import datetime
from collections import ChainMap

from experimentator.common import QuitSession
from experimentator.section import ExperimentSection

logger = getLogger(__name__)


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


def run_experiment_section(experiment, demo=False, resume=False, parent_callbacks=True,
                           section_obj=None, from_section=1, **section_numbers):
    """Run an experiment section.

    Runs an experiment instance from a file or an `Experiment` instance, and saves it. If a `QuitSession` exception is
    encountered, the `Experiment` will be backed up and saved before exiting the session.

    Arguments
    ---------
    experiment : str or Experiment
        File location where an `Experiment` instance is pickled, or an Experiment instance.
    demo : bool, optional
        If True, data will not be saved and sections will not be marked as run.
    resume: bool, optional
        If True, the specified section will be resumed (as opposed to starting at the beginning).
    parent_callbacks : bool, optional
            If True (the default), all parent callbacks will be called.
    section_obj : ExperimentSection, optional
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

    if not section_obj:
        section_obj = exp.subsection(**section_numbers)

    try:
        if resume:
            exp.resume_section(section_obj, demo=demo, parent_callbacks=parent_callbacks)
        else:
            exp.run_section(section_obj, demo=demo, parent_callbacks=parent_callbacks, from_section=from_section)
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


class Experiment(ExperimentSection):
    """Experiment.

    An `Experiment` instance handles all aspects of an experiment. It contains the entire experimental hierarchy and
    stores the data. It is picklable, to facilitate running an experiment over multiple Python sessions. `Experiment`
    is a subclass of `ExperimentSection`, so it can be indexed into, iterated over, etc.

    Arguments
    ---------
    tree : DesignTree
        A `DesignTree` instance defining the experiment hierarchy.
    experiment_file : str, optional
        A file location where the `Experiment` will be pickled.

    Attributes
    ----------
    tree : DesignTree
        The `DesignTree` instance defining the experiment's hierarchy.
    experiment_file : str
        The file location where the `Experiment` will be pickled.
    levels : list of str
        The levels of the experiment, as passed in `tree`.
    run_callback : func
        The function to be run when the bottom of the tree is reached (i.e., the trial function).
    context_managers : dict
        A dictionary, with level names as keys and context managers (e.g., created by `contextlib.contextmanager`) as
        values. Defines behavior to run before and/or after each section at the associated level.
    session_data : dict
        A dictionary where data can be stored that is persistent only within one session of the Python interpreter. This
        is a good place to store external resources that aren't picklable; external resources, for example, can be
        loaded in a context manager callback and stored here. In addition, anything yielded by a context manager will be
        automatically saved here, in `session_data['as'][level]`. Note that this dictionary is emptied before saving the
        `Experiment` to disk.
    experiment_data : dict
        A dictionary where data can be stored that is persistent across Python sessions. Everything here must be
        picklable.

    """
    def __init__(self, tree, experiment_file=None):
        tree.add_base_level()
        super().__init__(tree, ChainMap())

        self.experiment_file = experiment_file

        self.context_managers = {level: _dummy_context for level in self.levels}
        self.context_managers['_base'] = _dummy_context
        self._context_info = {level: None for level in self.levels}

        self.run_callback = _dummy_callback
        self._callback_info = None

        self.session_data = {'as': {}}
        self.experiment_data = {}

    def __repr__(self):
        return 'Experiment({}, experiment_file={})'.format(self.tree.__repr__(), self.experiment_file)

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
            self.dataframe.to_csv(f)

    def run_section(self, section, demo=False, parent_callbacks=True, from_section=None):
        """Run a section.

        Runs a section by descending the hierarchy and running each child section. Also calls the start, end, and inter
        callbacks where appropriate. Results are saved in each `ExperimentSection.data` attribute.

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

            >>> exp.run_section(exp.subsection(participant=1, session=2), from_section=[3, 5])

            Assuming the hierarchy is ``('participant', 'session', 'block', 'trial')``, this would run the first
            participant's second session, starting from the fifth trial of the third block.

        """
        logger.debug('Running {} with data {}.'.format(section.level, section.data))

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
                    logger.debug('Entering {} with data {}...'.format(parent.level, parent.data))
                    self.session_data['as'][parent.level] = stack.enter_context(self.context_managers[parent.level](
                        parent.data, session_data=self.session_data, experiment_data=self.experiment_data))

            # Back to the regular behavior.
            with self.context_managers[section.level](
                    section.data, session_data=self.session_data, experiment_data=self.experiment_data) as \
                    self.session_data['as'][section.level]:

                if not demo:
                    section.has_started = True

                if section.is_bottom_level:
                    results = self.run_callback(
                        section.data, session_data=self.session_data, experiment_data=self.experiment_data)
                    logger.debug('Results: {}.'.format(results))

                    if not demo:
                        section.add_data(results)

                else:  # Not bottom level.
                    for next_section in section[from_section[0]:]:
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
            start_at_numbers.append(start_at_section.data[level])

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

            parent_section_numbers.update({level: section.data[level]})
            yield self.subsection(**parent_section_numbers)

    def set_context_manager(self, level, func, *args,
                            func_module=None, func_name=None, already_contextmanager=False, **kwargs):
        """Set a context manager to run at a certain level.

        Defines a context manager to run at every section at a particular level. This is an alternative to start and end
        callbacks, to define behavior to occur at the beginning and end of every section. `func` should be a function
        that contains code to be run at the beginning of every section, followed by a ``yield`` statement, and then code
        to be run at the end of every section. Any return value from the ``yield`` statement will be saved in
        ``exp.session_data['as'][level]``.

        Alternatively, `func` can be a  contextmanager object (see the documentation for `contextlib`), in which case
        the flag ``already_contextmanager=True`` should be passed.

        Arguments
        ---------
        level : str
            Which level of the hierarchy to manage.
        func : func
            The context manager function.
        *args
            Any arbitrary positional arguments to be passed to `func`.
        func_module : str, optional
        func_name : str, optional
            These two arguments specify where the given function should be imported from in future Python sessions
            (i.e., ``from func_module import func_name``). Usually, this is figured out automatically by introspection,
            but these arguments are provided for the rare situation where introspection fails.
        already_contextmanager : bool, optional
           Pass True if `func` is already a contextmanager. Otherwise, it is assumed to be a generator function in the
           form required by `contextmanager`.
        **kwargs
            Any arbitrary keyword arguments to be passed to `func`.

        Note
        ----
        In addition to the arguments you set in `*args` and `**kwargs`, two positional arguments will be passed to
        `func`: `Experiment.session_data` and `Experiment.persistent_data`. Additionally, the items in the dictionary in
        the section's `ExperimentSection.data` attribute will be passed as keyword arguments. So the context manager
        should take the form of `(*args, session_data, persistent_data, **kwargs, **data)`, where `*args` and `**kwargs`
        come from this method, `session_data` and `persistent_data` come from the `Experiment` instance, and `data`
        comes from the `ExperimentSection` instance. Since the data can have many items, it is best practice to use
        the keyword argument wildcard `**` in your definition of `func`.

        """
        if not already_contextmanager:
            func = contextmanager(func)

        self.context_managers[level] = functools.partial(func, *args, **kwargs)
        self._context_info[level] = [list(_get_func_reference(func)), args, kwargs, already_contextmanager]

        if func_module:
            self._context_info[level][0][0] = func_module
        if func_name:
            self._callback_info[level][0][1] = func_name

    def set_run_callback(self, func, *args, func_module=None, func_name=None, **kwargs):
        """Set the run callback.

        Define a function to run at the lowest level of the experiment (i.e., the trial function).

        Arguments
        ---------
        func : func
            The function to be set as the run callback.
        *args
            Any arbitrary positional arguments to be passed to `func`.
        func_module : str, optional
        func_name : str, optional
            These two arguments specify where the given function should be imported from in future Python sessions
            (i.e., ``from func_module import func_name``). Usually, this is figured out automatically by introspection,
            but these arguments are provided for the rare situation where introspection fails.
        **kwargs
            Any arbitrary keyword arguments to be passed to `func`.

        Note
        ----
        In addition to the arguments you set in `*args` and `**kwargs`, two positional arguments will be passed to
        `func`: `Experiment.session_data` and `Experiment.persistent_data`. Additionally, the items in the dictionary in
        the section's `ExperimentSection.data` attribute will be passed as keyword arguments. So the run callback
        should take the form of `(*args, session_data, persistent_data, **kwargs, **data)`, where `*args` and
        `**kwargs` come from this method, `session_data` and `persistent_data` come from the `Experiment` instance, and
        `data` comes from the `ExperimentSection` instance. Since the data can have many items, it is best practice
        to use the keyword argument wildcard `**` in your definition of `func`.

        """
        self.run_callback = functools.partial(func, *args, **kwargs)
        self._callback_info = [list(_get_func_reference(func)), args, kwargs]

        if func_module:
            self._callback_info[0][0] = func_module
        if func_name:
            self._callback_info[0][1] = func_name

    def __getstate__(self):
        state = self.__dict__.copy()
        #  Clear session_data before pickling.
        state['session_data'] = {'as': {}}

        # Clear functions.
        del state['context_managers']
        del state['run_callback']

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

        self.run_callback = functools.partial(_load_func_reference(*self._callback_info[0]),
                                              *self._callback_info[1], **self._callback_info[2]) \
            if self._callback_info else _dummy_callback

        self.context_managers = {'_base': _dummy_context}
        for level in self.levels:
            if self._context_info[level]:
                func_info, func_args, func_kwargs, already_contextmanager = self._context_info[level]
                func = _load_func_reference(*func_info)

                if not already_contextmanager:
                    func = contextmanager(func)

                self.context_managers[level] = functools.partial(func, *func_args, **func_kwargs)

            else:
                self.context_managers[level] = _dummy_context


def _get_func_reference(func):
    if '__wrapped__' in func.__dict__:
        func = func.__wrapped__
    return os.path.basename(inspect.getsourcefile(func))[:-3], func.__name__


def _load_func_reference(module_name, func_name):
    try:
        module = import_module(module_name)
    except ImportError:
        logger.warning(("The original source of the callback '{}', '{}', doesn't seem to be in the current " +
                        "directory {}, or otherwise importable.").format(func_name, module_name, os.getcwd()))
        raise
    return getattr(module, func_name)


@contextmanager
def _dummy_context(*args, **kwargs):
    yield


def _dummy_callback(*args, **kwargs):
    return {}
