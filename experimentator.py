# Copyright (c) 2013 Henry S. Harrison

import numpy as np
import pandas as pd
import itertools
import functools
import collections
import logging


class SortError(Exception):
    pass


class DesignError(Exception):
    pass


class VariableError(Exception):
    pass


def make_sort_function(array, repeats, method):
    """
    array: iterable to be sorted
    repeats: number of times for each element in array to appear
    method: either a string {'random', more options to be implemented} or a list of indices
    """
    if method == 'random':
        return functools.partial(np.random.permutation, repeats * array)
    #TODO: More sorts (e.g. counterbalance)
    elif isinstance(method, str):
        raise SortError('Unrecognized sort method {}.'.format(method))
    elif not method:
        return lambda: repeats * array
    else:
            return lambda: repeats * np.array(array)[method]


class Variable():
    def __init__(self, name):
        logging.debug('Creating variable {} of type {}.'.format(name, type(self)))
        self.name = name

    def __str__(self):
        return self.name

    def value(self, *args, **kwargs):
        return None


class ConstantVariable(Variable):
    def __init__(self, name, value):
        super(ConstantVariable, self).__init__(name)
        self._value = value

    def value(self, idx):
        return self._value


class IndependentVariable(Variable):
    """
    Additional args: levels (list of values for the IV)
    Additional kwargs: design (between or within), change_by (trial, block, session, participant)
        design='between' is equivalent to change_by='participant'
    """
    def __init__(self, name, levels, design='within', change_by='trial'):
        super(IndependentVariable, self).__init__(name)
        self.levels = levels
        self.design = design
        if self.design == 'between':
            self.change_by = 'participant'
        elif self.design == 'within' and change_by == 'participant':
            raise DesignError('Cannot have a within-subjects IV change by participant.')
        else:
            self.change_by = change_by

    def value(self, idx, *args, **kwargs):
        return self.levels[idx]

    def __len__(self):
        return len(self.levels)

    def __getitem__(self, item):
        return self.levels[item]


class CustomVariable(Variable):
    def __init__(self, name, func):
        super(CustomVariable, self).__init__(name)
        self.func = func

    def value(self, idx):
        return self.func()


class RandomVariable(CustomVariable):
    def __init__(self, name, lower, upper):
        super(RandomVariable, self).__init__(name, lambda: (upper - lower)*np.random.random() + lower)


def new_variable(name, levels):
    logging.debug('Creating new variable from kwarg {}={}...'.format(name, levels))
    if callable(levels):
        return CustomVariable(name, levels)
    elif np.isscalar(levels):
        return ConstantVariable(name, levels)
    elif isinstance(levels, collections.abc.Iterable):
        return IndependentVariable(name, levels)
    else:
        raise VariableError('Cannot create variable {}={}.'.format(name, levels))


class Experiment():
    """
    Experiments should subclass this and override, at minimum, the method run_trial(trial_idx, **trial_settings).
    Other methods to override:
       session_start()
       session_end()
       block_start(block_idx, block) where block is a DataFrame with rows = trials
       block_end(block_idx, block)
       inter_block(block_idx, block) where block_idx and block refer to the next block
       inter_trial(trial_idx, **trial_settings) where trial_idx and trial_settings refer to the next trial

    Inputs to Experiment.__init__:
       *args: Variable objects
       **kwargs: output_names (column names in saved data, length = number of outputs returned by run_trial)
                 participant (participant number, for between-subjects experiments with deterministic participant order)
                 trial list settings:
                     trials_per_type_per_block {default = 1}
                     blocks_per_type {default = 1}
                     trial_sort, block_sort, participant_sort {'random' (default), array of indices}
                 Any number of name = value pairs, creating Variables.
                    ConstantVariable if value = constant
                    CustomVariable if value is callable
                    IndependentVariable (within-subjects) if value is iterable
    """
    # TODO: multi-session experiments
    def __init__(self, *args, output_names=None, participant=0, **kwargs):
        logging.info('Constructing new experiment...')
        self.output_names = output_names
        self.participant = participant

        trial_list_settings_defaults = {'trials_per_type_per_block': 1,
                                        'blocks_per_type': 1,
                                        'trial_sort': 'random',
                                        'block_sort': 'random',
                                        'participant_sort': None}
        self.trial_list_settings = {key: kwargs.pop(key, default)
                                    for key, default in trial_list_settings_defaults.items()}

        logging.info('Constructing variables...')
        self.unsorted_variables = list(args)
        for k, v in kwargs.items():
            self.unsorted_variables.append(new_variable(k, v))

        logging.info('Sorting variables by type...')
        filters = {'trial': lambda v: isinstance(v, IndependentVariable) and v.change_by == 'trial',
                   'block': lambda v: isinstance(v, IndependentVariable) and v.change_by == 'block',
                   'participant': lambda v: isinstance(v, IndependentVariable) and v.change_by == 'participant',
                   'non_iv': lambda v: not isinstance(v, IndependentVariable)}
        self.variables = {k: list(filter(v, self.unsorted_variables)) for k, v in filters.items()}
        logging.debug('Found {} trial IVs, {} block IVs, {} participant IVs, and {} other variables.'.format(
            len(self.variables['trial']), len(self.variables['block']), len(self.variables['participant']),
            len(self.variables['non_iv'])))

        self.n_blocks = 0
        self.n_trials = 0

        logging.info('Constructing blocks and trials...')
        self.blocks = list(self.block_list(**self.trial_list_settings))
        self.raw_results = []

    def cross_variables(self, vary_by):
        # We cross the indices of each IV's levels rather than the actual values.
        # This allows for subclasses to override the value method and do stuff besides indexing to determine the value.
        if self.variables[vary_by]:
            logging.debug('Crossing IVs that vary by {}...'.format(vary_by))
            iv_idxs = itertools.product(*[range(len(v)) for v in self.variables[vary_by]])
            return [{iv.name: iv.value(condition[idx]) for idx, iv in enumerate(self.variables[vary_by])}
                    for condition in iv_idxs]
        else:
            logging.debug('No IVs that vary by {}.'.format(vary_by))
            return [{}]

    def block_list(self, trials_per_type_per_block=1, blocks_per_type=1, trial_sort='random', block_sort='random',
                   participant_sort=None):
        types = {i: self.cross_variables(i) for i in ['trial', 'block', 'participant']}
        more_vars = lambda idx: {v.name: v.value(idx) for v in self.variables['non_iv']}

        # Constructing sort functions, rather than directly sorting, allows for a different sort for each call
        logging.debug('Creating sort method for participants within an experiment...')
        sort_experiment = make_sort_function(types['participant'], 1, participant_sort)
        logging.debug('Creating sort method for trials within a block...')
        sort_block = make_sort_function(types['trial'], trials_per_type_per_block, trial_sort)
        logging.debug('Creating sort method for blocks within a session...')
        sort_session = make_sort_function(types['block'], blocks_per_type, block_sort)

        logging.debug('Determining session variable values...')
        participants = sort_experiment()
        session_variables = participants[self.participant % len(participants)]
        if session_variables:
            logging.debug('Found {} session variables: {}.'.format(
                len(session_variables), ', '.join(session_variables)))
        else:
            logging.debug('Found 0 session variables.')

        logging.debug('Sorting blocks within session...')
        blocks = list(sort_session())
        self.n_trials = len(blocks) * len(sort_block())
        logging.debug('Constructing {} trials in {} blocks...'.format(self.n_trials, self.n_blocks))
        self.n_blocks = len(blocks)
        for block_idx, block in enumerate(blocks):
            logging.debug('Sorting trials within block {}...'.format(block_idx))
            trials = list(sort_block())
            for trial_idx, trial in enumerate(trials):
                # Add block-specific IVs, custom vars, and constants
                logging.debug('Constructing trial {}...'.format(trial_idx))
                trial.update(more_vars(block_idx*len(trials) + trial_idx))
                trial.update(block)
                trial.update(session_variables)
            yield pd.DataFrame(trials, index=block_idx*len(trials) + np.arange(len(trials)))

    def save_data(self, output_file):
        """
        Trial settings and results are combined into one DataFrame, which is pickled.
        """
        # Concatenate trial settings
        logging.debug('Combining trial inputs and outputs...')
        trial_inputs = pd.concat(self.blocks)

        results = pd.DataFrame(self.raw_results, columns=self.output_names)

        logging.debug('Writing data to file {}...'.format(output_file))
        pd.concat([trial_inputs, results], axis=1).to_pickle(output_file)

    def run_session(self, output_file):
        logging.info('Running session...')
        logging.debug('Running start_session()...')
        self.session_start()

        for block_idx, block in enumerate(self.blocks):
            logging.debug('Block {}:'.format(block_idx))
            if block_idx > 1:
                logging.debug('Running inter_block()...')
                self.inter_block(block_idx, block)
            logging.debug('Running block_start()')
            self.block_start(block_idx, block)

            for trial_idx, trial in block.iterrows():
                if trial_idx > 0:
                    logging.debug('Running inter_trial()...')
                    self.inter_trial(trial_idx, **dict(trial))
                logging.info('Running trial {}...'.format(trial_idx))
                self.raw_results.append(self.run_trial(trial_idx, **dict(trial)))

            logging.debug('Running block_end()')
            self.block_end(block_idx, block)
        logging.debug('Running session_end()')
        self.session_end()

        logging.info('Saving data...')
        self.save_data(output_file)

    def run_trial(self, trial_idx, **kwargs):
        return None

    def block_start(self, block_idx, block):
        pass

    def block_end(self, block_idx, block):
        pass

    def inter_block(self, block_idx, block):
        pass

    def session_start(self):
        pass

    def session_end(self):
        pass

    def inter_trial(self, current_trial, **kwargs):
        pass