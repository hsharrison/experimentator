# Copyright (c) 2013 Henry S. Harrison
"""
A module for running experiments.

The basic use case is that you have already written code to run a single trial and would like to run a set of
experimental sessions in which inputs to your trial function are systematically varied and repeated.


"""

import re
import itertools
import collections
import logging
import pickle
import random
from configparser import ConfigParser

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


def parse_config(config_file):
    """
    Parse config file(s) for experiment information.

    [Experiment]
    levels = comma-separated list
    sort methods = list, separated by commas or semicolons (for use when one or more sort method includes a comma)
    number = comma-separated list of integers

    [Independent Variables]
    variable name = level, comma- or semicolon-separated list of values

    That is, each entry name in the Independent Variables section is interpreted as a variable name. The entry string is
    interpreted as a comma- or semicolon-separated. The first element should match one of the levels specified in the
    Experiment section. The other elements are the possible values (levels) of the IV. These values are interpreted by
    the Python interpreter, so proper syntax should be used for values that aren't simple strings or numbers.
    """
    config = ConfigParser()
    config.read_file(config_file)
    levels = config['Experiment']['levels'].split(',')
    sort_methods = config['Experiment']['sort methods'].split(',')
    number = config['Experiment']['number'].split(',')

    # Allow for use of ';' in sort, so sequences can be input
    if len(sort_methods) != len(levels):
        sort_methods = config['Experiment']['sort methods'].split(';')
    # Allow for non-string sort methods, check by looking for non-alphanumeric characters
    sort_methods = [sort if re.match('\w+$', sort) else eval(sort) for sort in sort_methods]

    settings_by_level = {level: dict(sort=sort, number=int(n), ivs={})
                         for level, sort, n in zip(levels, sort_methods, number)}

    for name, entry in config['Independent Variables'].items():
        entry_split = entry.split(',')
        # Allow for ; in variable lists
        if entry_split[0] not in levels:
            entry_split = entry.split(';')

        settings_by_level[entry_split[0]]['ivs'][name] = list(eval(entry) for entry in entry_split[1:])

    return levels, settings_by_level


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
        loaded_from_file = False
        exp = experiment
    else:
        loaded_from_file = True
        exp = load_experiment(experiment)

    if not section:
        section = exp.find_section(**kwargs)

    try:
        exp.run(section, demo=demo)
    except QuitSession as e:
        logging.warning('Quit event detected: {}.'.format(str(e)))
    finally:
        if loaded_from_file:
            exp.save(experiment)


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
        children:          A list of ExperimentSection instances.
        context:           A ChainMap of IV name: value mappings that apply to all of the section's children.
        level:             The current level.
        results:           (lowest level only) The results, as a dict which includes the IV values and section numbers.
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
                                sort:  sort method, string (e.g., 'random'), sequence of indices, or None
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
            self.results = self.context
        else:
            self.results = None
            self.next_level = levels[1]
            self.next_settings = settings_by_level.get(self.next_level, dict())
            self.next_level_inputs = (levels[1:], settings_by_level)

            # Create the section tree. Creating any section also creates the sections below it
            for i, section_context in enumerate(self.get_child_contexts()):
                child_context = self.context.new_child()
                child_context.update(section_context)
                child_context[self.next_level] = i+1
                logging.debug('Generating {} with context {}.'.format(self.next_level, child_context))
                self.children.append(ExperimentSection(child_context, *self.next_level_inputs))

    def get_child_contexts(self):
        """
        Crosses the section's independent variables, and sorts and repeats the unique combinations to yield the
        context for the section's children.
        """
        ivs = self.next_settings.get('ivs', dict())
        iv_combinations = itertools.product(*[v for v in ivs.values()])
        unique_contexts = [{k: v for k, v in zip(ivs, condition)} for condition in iv_combinations]
        logging.debug('Sorting {} with unique contexts {}.'.format(self.next_level, unique_contexts))
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
            # Try to index as the last resort
            yield from n * list(unique_contexts[idx] for idx in method)

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

    def add_data(self, data_dict):
        """
        Add data to all trials in a section. For example, add participant information to all entries under that
        participant.
        """
        if self.is_bottom_level:
            self.results.update(data_dict)
        else:
            for child in self.children:
                child.add_data(data_dict)

    def generate_data(self):
        for child in self.children:
            if child.is_bottom_level:
                yield child.results
            else:
                yield from child.generate_data


class Experiment(metaclass=collections.abc.ABCMeta):
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
        output_names:      A list naming each DV (outputs of the run_trial method).
        root:              An ExperimentSection instance from which all experiment sections descend.
        data:              A pandas DataFrame. Before any sections are run, contains only the IV values of each trial.
                           Afterwards, contains both IV and DV values.

    """
    def __init__(self, settings_by_level,
                 levels=('participant', 'session', 'block', 'trial'),
                 experiment_file=None,
                 output_names=None,
                 ):
        """
        Initialize an Experiment instance.

        Args:
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
            output_names=None:    A list naming each DV (outputs of the run_trial method). Will be column labels on the
                                  data DataFrame.
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
        data = pd.DataFrame(self.root.generate_data()).set_index(list(self.levels))
        return data

    def save(self, filename):
        logging.debug('Saving Experiment instance to {}.'.format(filename))
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

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

    def find_first_not_run(self, at_level, by_started=True):
        """
        Search through all sections at the specified level, and return the first not already run. If by_started=True, a
        section is considered already run if it has started. Otherwise, it is considered already run only if it has
        finished.
        """
        attribute = {True: 'has_started', False: 'has_finished'}[by_started]
        node = self.root
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

    def run(self, section, demo=False):
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
        section.has_started = True
        if section.is_bottom_level:
            results = self.run_trial(**section.context)
            logging.debug('Results: {}.'.format(results))
            if not demo:
                section.results.update({n: r for n, r in zip(self.output_names, results)})
        else:
            self.start(section.level, **section.context)
            for i, next_section in enumerate(section.children):
                if i:
                    self.inter(next_section.level, **next_section.context)
                self.run(next_section)
            self.end(section.level, **section.context)
        section.has_finished = True

    def start(self, level, **kwargs):
        pass

    def end(self, level, **kwargs):
        pass

    def inter(self, level, **kwargs):
        pass

    @collections.abc.abstractmethod
    def run_trial(self, **kwargs):
        return None, None
