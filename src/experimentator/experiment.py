"""
This module contains the |Experiment| class and associated helper functions.
Public objects are imported in ``__init__.py``.

"""
import os
import pickle
import inspect
from logging import getLogger
from importlib import import_module
from contextlib import contextmanager, ExitStack
from datetime import datetime
from collections import namedtuple

from experimentator import yaml
from experimentator.section import ExperimentSection
from experimentator.design import DesignTree, Design
import experimentator.order as order

logger = getLogger(__name__)
FunctionReference = namedtuple('FunctionReference', ('module', 'name'))


def run_experiment_section(experiment, section_obj=None, demo=False, resume=False, parent_callbacks=True,
                           from_section=1, session_options='', **section_numbers):
    """
    Run an experiment from a file or an |Experiment| instance, and save it.
    If an exception is encountered, the |Experiment| will be backed up and saved.

    Parameters
    ----------
    experiment : str or |Experiment|
        File location where an |Experiment| instance is pickled, or an |Experiment| instance.
    demo : bool, optional
        If True, data will not be saved and sections will not be marked as run.
    resume: bool, optional
        If True, the specified section will be resumed (started automatically where it left off).
    parent_callbacks : bool, optional
        If True (the default), all parent callbacks will be called.
    section_obj : |ExperimentSection|, optional
        The section of the experiment to run.
        Alternatively, the section can be specified using `**section_numbers`.
    from_section : int or list of int, optional
        Which section to start running from.
        If a list is passed, it specifies where to start running on multiple levels.
        See the example below.
    session_options : str, optional
        Pass an experiment-specific options string to be stored in |Experiment.session_data|
        under the key ``'options'``.
    **section_numbers
        Keyword arguments describing how to descend the experiment hierarchy to find the section to run.
        See the example below.

    Examples
    --------
    A simple example:
        >>> exp = Experiment.load('example.exp')
        >>> run_experiment_section(exp, exp.subsection(participant=1, session=2))

    Equivalently:

        >>> run_experiment_section(exp, participant=1, session=2)

    To demonstrate `from_section`,
    assuming the experiment hierarchy is ``('participant', 'session', 'block', 'trial')``,
    this would start from the second block:

        >>> run_experiment_section(exp, participant=1, session=2, from_section=2)

    To start from the fifth trial of the second block:

        >>> run_experiment_section(exp, participant=1, session=2, from_section=[2, 5])

    """
    if isinstance(experiment, Experiment):
        exp = experiment
    else:
        exp = Experiment.load(experiment)
    exp.session_data['options'] = session_options

    if not section_obj:
        section_obj = exp.subsection(**section_numbers)

    try:
        if resume:
            exp.resume_section(section_obj, demo=demo, parent_callbacks=parent_callbacks)
        else:
            exp.run_section(section_obj, demo=demo, parent_callbacks=parent_callbacks, from_section=from_section)

    except:
        logger.warning('Exception occurred, saving backup.')
        # Backup experiment file.
        os.rename(exp.filename,
                  exp.filename + datetime.now().strftime('.%m-%d-%H-%M-backup'))
        raise

    finally:
        exp.save()


def export_experiment_data(exp_filename, data_filename, **kwargs):
    """
    Reads a pickled |Experiment| instance and saves its data in ``.csv`` format.

    Parameters
     ----------
    exp_filename : str
        The file location where an |Experiment| instance is pickled.
    data_filename : str
        The file location where the data will be written.
    skip_columns : list of str, optional
        Data columns to skip.
    **kwargs
        Arbitrary keyword arguments passed through to |DataFrame.to_csv|.

    Notes
    -----
    This shortcut function is not recommended for experiments with compound data types,
    for example an experiment which stores a time series for every trial.
    In such cases it is recommended to write a custom script
    that parses |Experiment.dataframe| as desired
    (or use the `skip_columns` option to ignore the compound data).

    """
    Experiment.load(exp_filename).export_data(data_filename, **kwargs)


class Experiment(ExperimentSection):
    """
    An |ExperimentSection| subclass that represents the largest 'section' of the experiment;
    that is, the entire experiment.
    Functionality added on top of |ExperimentSection| includes
    various constructors, saving to disk, and management of |callbacks|.

    To create a new experiment, rather than instantiating directly
    it is recommended to use one of the constructor methods:

        - |Experiment.new|
        - |Experiment.from_dict|
        - |Experiment.from_yaml_file|
        - |Experiment.within_subjects|
        - |Experiment.blocked|
        - |Experiment.basic|

    Attributes
    ----------
    tree : |DesignTree|
        The |DesignTree| instance defining the experiment's hierarchy.
    filename : str
        The file location where the |Experiment| will be pickled.
    callback_by_level : dict
        A dictionary, mapping level names to functions or |context-managers|
        (e.g., generator functions decorated with |contextlib.contextmanager|).
        Defines behavior to run at each section (for functions)
        or before and/or after each section (for context managers) at the associated level.
    callback_type_by_level : dict
        A dictionary mapping level names to either the string ``'context'`` or ``'function'``.
        This keeps track of which callbacks in |Experiment.callback_by_level| are context managers.
    session_data : dict
        A dictionary where temporary data can be stored,
        persistent only within one session of the Python interpreter.
        This is a good place to store external resources that aren't |picklable|;
        external resources, for example, can be loaded in a |context-manager| callback and stored here.
        In addition, anything returned by the ``__exit__`` method of a |context-manager| callback
        will be stored here, with the callback's level name as the key.
        This dictionary is emptied before saving the |Experiment| to disk.
    experiment_data : dict
        A dictionary where data can be stored that is persistent across Python sessions.
        Everything stored here must be |picklable|.

    """
    def __init__(self, tree,
                 data=None,
                 has_started=False,
                 has_finished=False,
                 _children=None,
                 filename=None,
                 callback_by_level=None,
                 callback_type_by_level=None,
                 session_data=None,
                 experiment_data=None,
                 _callback_info=None,
                 ):
        super().__init__(tree, data=data, has_started=has_started, has_finished=has_finished, _children=_children)
        self.filename = filename
        self.callback_by_level = {} if callback_by_level is None else callback_by_level
        self.callback_type_by_level = {} if callback_type_by_level is None else callback_type_by_level
        self.session_data = {} if session_data is None else session_data
        self.experiment_data = {} if experiment_data is None else experiment_data
        self._callback_info = {} if _callback_info is None else _callback_info

    @classmethod
    def new(cls, tree, filename=None):
        """Make a new |Experiment|.

        Parameters
        ----------
        tree : |DesignTree|
            A |DesignTree| instance defining the experiment hierarchy.
        filename : str, optional
            A file location where the |Experiment| will be saved.

        """
        tree.add_base_level()
        self = super(Experiment, cls).new(tree)
        self.filename = filename
        return self

    @staticmethod
    def load(filename):
        """
        Load an experiment from disk.

        Parameters
        ----------
        filename : str
            Path to a file generated by |Experiment.save|.

        Returns
        -------
        |Experiment|

        """
        with open(filename, 'r') as f:
            self = yaml.load(f)
        self.filename = filename
        return self

    @classmethod
    def from_dict(cls, spec):
        """
        Construct an |Experiment| based on a dictionary specification.

        Parameters
        ----------
        spec : dict
            `spec` should have, at minimum, a key named ``'design'``.
            The value of this key specifies the |DesignTree|.
            See |DesignTree.from_spec| for details.
            The value of the key ``'filename'`` or ``'file'``, if one exists,is saved in |Experiment.filename|.
            All other fields are saved in |Experiment.experiment_data|.

        Returns
        -------
        |Experiment|

        See Also
        --------
        experimentator.Experiment.from_yaml_file

        """
        tree = DesignTree.from_spec(spec.pop('design'))
        filename = spec.pop('filename', spec.pop('file', None))
        self = cls.new(tree, filename=filename)
        self.experiment_data = spec
        return self

    @classmethod
    def from_yaml_file(cls, filename):
        """
        Construct an |Experiment| based on specification in a YAML file.
        Requires `PyYAML`_.

        Parameters
        ----------
        filename : str
            YAML file location.
            The YAML should specify a dictionary matching the specification of |Experiment.from_dict|.

        Returns
        -------
        |Experiment|

        """
        if not yaml:
            raise ImportError('PyYAML is not installed')
        with open(filename, 'r') as f:
            spec = yaml.load(f)
        return cls.from_dict(spec)

    @classmethod
    def within_subjects(cls, ivs, n_participants, design_matrix=None, ordering=None, filename=None):
        """
        Create a within-subjects |Experiment|, with all the IVs at the |trial| level.

        Parameters
        ----------
        ivs : list or dict
            A list of the experiment's IVs, specified in the form of tuples
            with the first element being the IV name and the second element a list of its possible values.
            Alternatively, the IVs at each level can be specified in a dictionary.
            See the |IV docs| more on specifying IVs.
        n_participants : int
            Number of participants to initialize.
        design_matrix : array-like, optional
            Design matrix for the experiment. If not specified, IVs will be fully crossed.
            See the |design matrix docs| for more details.
        ordering : |Ordering|, optional
            An instance of the class |Ordering| or one of its subclasses, specifying how the trials will be ordered.
            If not specified, |Shuffle| will be used.
        filename : str, optional
            File location to save the experiment.

        Returns
        -------
        |Experiment|

        """
        levels_and_designs = [('participant', [Design(ordering=order.Shuffle(n_participants))]),
                              ('trial', [Design(ivs=ivs, design_matrix=design_matrix, ordering=ordering)])]

        return cls.new(DesignTree.new(levels_and_designs), filename=filename)

    @classmethod
    def blocked(cls, trial_ivs, n_participants, design_matrices=None, orderings=None, block_ivs=None, filename=None):
        """Create a blocked within-subjects |Experiment|,
        in which all the IVs are at either the trial level or the block level.

        Parameters
        ----------
        trial_ivs : list or dict
            A list of the IVs to define at the trial level, specified in the form of tuples
            with the first element being the IV name and the second element a list of its possible values.
            Alternatively, the IVs at each level can be specified in a dictionary.
            See the |IV docs| more on specifying IVs.
        n_participants : int
            Number of participants to initialize.
            If a |NonAtomicOrdering| is used,
            this is the number of participants per order.
        design_matrices : dict, optional
            Design matrices for the experiment.
            Keys are ``'trial'`` and ``'block'``; values are the respective design matrices (if any).
            If not specified, IVs will be fully crossed.
            See the |design matrix docs| for details.
        orderings : dict, optional
            Dictionary with keys of ``'trial'`` and ``'block'``.
            Each value should be an instance of the class |Ordering| or one of its subclasses,
            specifying how the trials will be ordered
            If not specified, |Shuffle| will be used.
        block_ivs : list or dict, optional
            IVs to define at the block level.
            See |IV docs| for more on specifying IVs.
        filename : str, optional
            File location to save the experiment.

        Notes
        -----
        For blocks to have any effect,
        you should either define at least one IV at the block level
        or use the ordering ``Ordering(n)`` to create ``n`` blocks for every participant.

        Returns
        -------
        |Experiment|

        """
        if not design_matrices:
            design_matrices = {}
        if not orderings:
            orderings = {}

        levels_and_designs = [('participant', [Design(ordering=order.Shuffle(n_participants))]),
                              ('block', [Design(ivs=block_ivs,
                                                design_matrix=design_matrices.get('block'),
                                                ordering=orderings.get('block'))]),
                              ('trial', [Design(ivs=trial_ivs,
                                                design_matrix=design_matrices.get('trial'),
                                                ordering=orderings.get('trial'))])]

        return cls.new(DesignTree.new(levels_and_designs), filename=filename)

    @classmethod
    def basic(cls, levels, ivs_by_level, design_matrices_by_level=None, ordering_by_level=None, filename=None):
        """Construct a homogeneously-organized |Experiment|,
        with arbitrary levels but only one |Design| at each level,
        and the same structure throughout its hierarchy.

        Parameters
        ----------
        levels : sequence of str
            Names of the levels of the experiment
        ivs_by_level : dict
            Dictionary specifying the IVs and their possible values at every level.
            The keys are be the level names,
            and the values are lists of the IVs at that level,
            specified in the form of tuples with the first element being the IV name
            and the second element a list of its possible values.
            Alternatively, the IVs at each level can be specified in a dictionary.
            See |IV docs| for more on specifying IVs.
        design_matrices_by_level : dict, optional
            Specify the design matrix for any levels.
            Keys are level names; values are design matrices.
            Any levels without a design matrix will be fully crossed.
            See |design matrix docs| for details.
        ordering_by_level : dict, optional
            Specify the ordering for each level.
            Keys are level names; values are instance objects from |experimentator.order|.
            For any levels without an order specified, |Shuffle| will be used.
        filename : str, optional
            File location to save the experiment.

        Returns
        -------
        |Experiment|

        """
        if not design_matrices_by_level:
            design_matrices_by_level = {}
        if not ordering_by_level:
            ordering_by_level = {}

        levels_and_designs = [(level, [Design(ivs=ivs_by_level.get(level),
                                       design_matrix=design_matrices_by_level.get(level),
                                       ordering=ordering_by_level.get(level))])
                              for level in levels]

        return cls.new(DesignTree.new(levels_and_designs), filename=filename)

    def save(self, filename=None):
        """Save the |Experiment| to disk.

        Parameters
        ----------
        filename : str, optional
            If specified, overrides |Experiment.filename|.

        """
        filename = filename or self.filename
        if filename:
            logger.debug('Saving Experiment instance to {}.'.format(filename))
            with open(filename, 'w') as f:
                yaml.dump(self, f)

        else:
            logger.warning('Cannot save experiment: No filename provided.')

    def export_data(self, filename, skip_columns=None, **kwargs):
        """
        Export |Experiment.dataframe| in ``.csv`` format.

        Parameters
        ----------
        filename : str
            A file location where the data should be saved.
        skip_columns : list of str, optional
            Columns to skip.
        **kwargs
            Arbitrary keyword arguments to pass to |DataFrame.to_csv|.

        Notes
        -----
        This method is not recommended for experiments with compound data types,
        for example an experiment which stores a time series for every trial.
        In those cases it is recommended to write a custom script
        that parses the |Experiment.dataframe| attribute as desired,
        or use the `skip_columns` option to skip any compound columns.

        """
        df = self.dataframe
        if skip_columns:
            kwargs['columns'] = set(df.columns) - set(skip_columns)

        with open(filename, 'w') as f:
            df.to_csv(f, **kwargs)

    def run_section(self, section, demo=False, parent_callbacks=True, from_section=None):
        """
        Run a section and all its descendant sections.
        Saves the results in the |data| attribute of each lowest-level |ExperimentSection|.

        Parameters
        ----------
        section : |ExperimentSection|
            The section to be run.
        demo : bool, optional
            Data will only be saved if `demo` is False (the default).
        parent_callbacks : bool, optional
            If True (the default), all parent callbacks will be called.
        from_section : int or list of int, optional
            Which section to start running from.
            If a list is passed, it specifies where to start running on multiple levels.
            For example, assuming the experiment hierarchy is ``('participant', 'session', 'block', 'trial')``,
            this would start from the fifth trial of the second block (of the first participant's second session):

                >>> exp = Experiment.load('example.exp')
                >>> exp.run_section(exp.subsection(participant=1, session=2), from_section=[2, 5])

        Notes
        -----
        The wrapper function :func:`run_experiment_section` should be used instead of this method, if possible.

        """
        logger.debug('Running {}.'.format(section.description))

        with ExitStack() as stack:
            stack.enter_context(self._parent_context(section, parent_callbacks=parent_callbacks, demo=demo))
            stack.enter_context(self._section_context(section, demo=demo))

            if len(section):  # If the section has children.
                from_section, next_from_section = self._parse_from_section(from_section)
                for next_section in section[from_section[0]:]:
                    self.run_section(next_section,
                                     demo=demo,
                                     parent_callbacks=False,
                                     from_section=next_from_section)

            if not demo:
                section.has_finished = True

            if parent_callbacks:
                logger.debug('Exiting all parent levels...')

        # Finished parents detection.
        if not section.level == '_base':
            for parent in reversed(list(self.parents(section))):
                if all(child.has_finished for child in parent):
                    parent.has_finished = True

    @contextmanager
    def _section_context(self, section, demo=False):
        with ExitStack() as stack:
            if not demo:
                section.has_started = True

            if self.callback_type_by_level.get(section.level) == 'context':
                self.session_data[section.level] = stack.enter_context(
                    self.callback_by_level[section.level](self, section)
                )

            elif self.callback_type_by_level.get(section.level) == 'function':
                results = self.callback_by_level[section.level](self, section)
                if results and not demo:
                    section.add_data(results)

            yield

    @staticmethod
    def _parse_from_section(from_section):
        if isinstance(from_section, int):
            from_section = [from_section]
        if from_section is None:
            from_section = [1]
        if len(from_section) > 1:
            next_from_section = from_section[1:]
        else:
            next_from_section = [1]
        return from_section, next_from_section

    @contextmanager
    def _parent_context(self, section, parent_callbacks=True, demo=False):
        with ExitStack() as stack:
            for parent in self.parents(section):
                if parent_callbacks:
                    logger.debug('Entering {} context.'.format(parent.description))
                    stack.enter_context(self._section_context(parent, demo=demo))
            yield

    def resume_section(self, section, **kwargs):
        """Rerun a section that has been started but not finished, starting where running last left off.

        Parameters
        ----------
        section : |ExperimentSection|
            The section to resume.
        **kwargs
            Keyword arguments to pass to |Experiment.run_section|.

        Notes
        -----
        The wrapper function |run_experiment_section| should be used instead of this method, if possible.

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
            start_at_section = start_at_section.find_first_not_run(level)
            start_at_numbers.append(start_at_section.data[level])

        self.run_section(section, from_section=start_at_numbers, **kwargs)

    def add_callback(self, level, callback, *args, is_context=False, func_module=None, func_name=None, **kwargs):
        """Add a callback to run at a certain level.

        A callback can be either a regular function, or a |context-manager|.
        The latter is useful for defining code to run at the start and end of every section at the level.
        For example, a block context manager could specify behavior that occurs before every trial in the block,
        and behavior that occurs after every trial in the block.
        See |contextlib| for various ways to create context managers,
        and experimentator's |context-manager docs| for more details.

        Any value returned by the ``__enter__`` method of a context manager
        will be stored in |Experiment.session_data| under the key `level`.

        If the callback is not a context manager, it should return a dictionary (or nothing),
        which is automatically passed to |ExperimentSection.add_data|.
        In theory, it should map dependent-variable names to results.
        See the |callback docs| for more details.

        Parameters
        ----------
        level : str
            Which level of the hierarchy to manage.
        callback : function or |context-manager|
            The callback should have the signature ``callback(experiment, section, *args, **kwargs)``
            where `experiment` and `section`
            are the current |Experiment| and |ExperimentSection| instances, respectively,
            and `args` and `kwargs` are arbitrary arguments passed to this method.
        *args
            Any arbitrary positional arguments to be passed to `callback`.
        func_module : str, optional
        func_name : str, optional
            These two arguments specify where the given function should be imported from in future Python sessions
            (i.e., ``from <func_module> import <func_name>``).
            Usually, this is figured out automatically by introspection;
            these arguments are provided for the rare situation where introspection fails.
        **kwargs
            Any arbitrary keyword arguments to be passed to `callback`.

        """
        self.callback_by_level[level] = _callback_partial(callback, args, kwargs)
        self.callback_type_by_level[level] = 'context' if is_context else 'function'

        reference = _get_func_reference(callback)
        reference = FunctionReference(func_module or reference[0], func_name or reference[1])
        self._callback_info[level] = [reference, args, kwargs]

    def __getstate__(self):
        state = self.__dict__.copy()
        #  Clear session_data before pickling.
        state['session_data'] = {}

        # Clear functions.
        del state['callback_by_level']

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

        # Reload callbacks.
        self.callback_by_level = {level: _callback_partial(*self._callback_info[level])
                                  for level in self._callback_info}


def _get_func_reference(func):
    if '__wrapped__' in func.__dict__:
        func = func.__wrapped__
    return FunctionReference(os.path.basename(inspect.getsourcefile(func))[:-3], func.__name__)


def _load_func_reference(module_name, func_name):
    try:
        module = import_module(module_name)
    except ImportError:
        logger.warning(("The original source of the callback '{}', '{}', doesn't seem to be in the current " +
                        "directory {}, or otherwise importable.").format(func_name, module_name, os.getcwd()))
        raise
    return getattr(module, func_name)


def _callback_partial(func, args, kwargs):
    if isinstance(func, FunctionReference):
        func = _load_func_reference(*func)
    return lambda experiment, section: func(experiment, section, *args, **kwargs)
