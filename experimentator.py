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
    else:
            return lambda: repeats * np.array(array)[method]


class Variable():
    def __init__(self, name):
        logging.info('Creating variable %s of type %s.', name, type(self))
        self.name = name

    def __str__(self):
        return self.name

    def value(self, *args, **kwargs):
        return None


class ConstantVariable(Variable):
    def __init__(self, name, value):
        super(ConstantVariable, self).__init__(name)
        self._value = value

    def value(self):
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

    def value(self, idx):
        return self.levels[idx]

    def __len__(self):
        return len(self.levels)


class CustomVariable(Variable):
    def __init__(self, name, func):
        super(CustomVariable, self).__init__(name)
        self.func = func

    def value(self):
        return self.func()


class RandomVariable(CustomVariable):
    def __init__(self, name, lower, upper):
        super(RandomVariable, self).__init__(name, lambda: (upper - lower)*np.random.random() + lower)


def new_variable(name, levels):
    logging.info('Creating new variable from kwarg %s=%s...', name, levels)
    if callable(levels):
        return CustomVariable(name, levels)
    elif np.isscalar(levels):
        return ConstantVariable(name, levels)
    elif isinstance(levels, collections.abc.Iterable):
        return IndependentVariable(name, levels)
    else:
        raise VariableError('Cannot create variable {} = {}'.format(name, levels))


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
                 trial list settings:
                     trials_per_type_per_block {default = 1}
                     blocks_per_type {default = 1}
                     trial_sort {'random' (default), array of indices}
                     block_sort {'random' (default), array of indices}
                 Any number of name = value pairs, creating Variables.
                    ConstantVariable if value = constant
                    CustomVariable if value is callable
                    IndependentVariable (within-subjects) if value is iterable
    """
    # TODO: between-subjects design
    # TODO: multi-session experiments
    def __init__(self, *args, output_names=None, **kwargs):
        logging.info('Constructing new experiment...')
        self.output_names = output_names

        trial_list_settings_defaults = {'trials_per_type_per_block': 1,
                                        'blocks_per_type': 1,
                                        'trial_sort': 'random',
                                        'block_sort': 'random'}
        self.trial_list_settings = {key: kwargs.pop(key, default)
                                    for key, default in trial_list_settings_defaults.items()}

        logging.info('Constructing variables...')
        self.variables = list(args)
        for k, v in kwargs.items():
            self.variables.append(new_variable(k, v))

        logging.info('Sorting variables by type...')
        self.trial_ivs = [v for v in self.variables if isinstance(v, IndependentVariable) and v.change_by == 'trial']
        self.block_ivs = [v for v in self.variables if isinstance(v, IndependentVariable) and v.change_by == 'block']
        self.constants = [v for v in self.variables if isinstance(v, ConstantVariable)]
        self.custom_vars = [v for v in self.variables if isinstance(v, CustomVariable)]

        self.n_blocks = 0
        self.n_trials = 0

        logging.info('Constructing blocks and trials...')
        self.blocks = list(self.block_list(**self.trial_list_settings))
        self.raw_results = []

    def block_list(self, trials_per_type_per_block=1, blocks_per_type=1, trial_sort='random', block_sort='random'):
        # In this and the next block, we cross the indices of each IV's levels rather than the actual values.
        # This allows for subclasses to override the value method and do stuff besides indexing to determine the value.
        if self.trial_ivs:
            logging.info('Crossing IVs that vary by trial...')
            iv_idxs = itertools.product(*[range(len(v)) for v in self.trial_ivs])
            trial_types = [{iv.name: iv.value(condition[idx]) for idx, iv in enumerate(self.trial_ivs)}
                           for condition in iv_idxs]
        else:
            logging.info('No IVs that vary by trial.')
            trial_types = [{}]

        if self.block_ivs:
            logging.info('Crossing IVs that vary by block...')
            iv_idxs = itertools.product(*[range(len(v)) for v in self.block_ivs])
            block_types = [{iv.name: iv.value(condition[idx]) for idx, iv in enumerate(self.block_ivs)}
                           for condition in iv_idxs]
        else:
            logging.info('No IVs that vary by block.')
            block_types = [{}]

        # TODO: Pass any args/kwargs to custom_vars.value?
        more_vars = lambda idx: {v.name: v.value() for v in np.concatenate((self.custom_vars, self.constants))}

        # Constructing sort functions, rather than directly sorting, allows for a different sort for each call
        logging.info('Creating sort method for trials within a block...')
        sort_block = make_sort_function(trial_types, trials_per_type_per_block, trial_sort)
        logging.info('Creating sort method for blocks within a session...')
        sort_session = make_sort_function(block_types, blocks_per_type, block_sort)

        logging.info('Constructing blocks within session...')
        blocks = list(sort_session())
        self.n_trials = len(blocks) * len(sort_block())
        self.n_blocks = len(blocks)
        for block_idx, block in enumerate(blocks):
            logging.info('Constructing trials within block %s...', block_idx)
            trials = list(sort_block())
            for trial_idx, trial in enumerate(trials):
                # Add block-specific IVs, custom vars, and constants
                logging.info('Constructing trial %s...', trial_idx)
                trial.update({k: v for k, v in block.items()})
                trial.update(more_vars(block_idx*len(trials) + trial_idx))
            yield pd.DataFrame(trials, index=block_idx*len(trials) + np.arange(len(trials)))

    def save_data(self, output_file):
        """
        Trial settings and results are combined into one DataFrame, which is pickled.
        """
        # Concatenate trial settings
        logging.info('Combining trial inputs and outputs...')
        trial_inputs = pd.concat(self.blocks)

        results = pd.DataFrame(self.raw_results, columns=self.output_names)

        logging.info('Writing data to file %s...', output_file)
        pd.concat([trial_inputs, results], axis=1).to_pickle(output_file)

    def run_session(self, output_file):
        logging.info('Running session...')
        logging.info('Running start_session()...')
        self.session_start()

        for block_idx, block in enumerate(self.blocks):
            logging.info('Block %s:', block_idx)
            if block_idx > 1:
                logging.info('Running inter_block()...')
                self.inter_block(block_idx, block)
            logging.info('Running block_start()')
            self.block_start(block_idx, block)

            for trial_idx, trial in block.iterrows():
                logging.info('Trial %s:', trial_idx)
                if trial_idx > 0:
                    logging.info('Running inter_trial()...')
                    self.inter_trial(trial_idx, **dict(trial))
                logging.info('Running trial...')
                self.raw_results.append(self.run_trial(trial_idx, **dict(trial)))

            logging.info('Running block_end()')
            self.block_end(block_idx, block)
        logging.info('Running session_end()')
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