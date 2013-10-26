import numpy as np
import pandas as pd
import itertools
import functools


class SortError(Exception):
    pass


class DesignError(Exception):
    pass


def make_sort_function(array, repeats, method):
    """
    array: iterable to be sorted
    repeats: number of times for each element in array to appear
    method: either a string {'random', more options to be implemented} or a list of indices same length as array
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
        self.name = name

    def __str__(self):
        return self.name

    def value(self, *args, **kwargs):
        return None


class ConstantVariable(Variable):
    def __init__(self, name, value):
        super(ConstantVariable, self).__init__(name)
        self._value = value

    def value(self, *args, **kwargs):
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
    if callable(levels):
        return CustomVariable(name, levels)
    elif np.isscalar(levels):
        return ConstantVariable(name, levels)
    else:
        return IndependentVariable(name, levels)


class Experiment():
    """
    Experiments should subclass this and override, at minimum, the method run_trial(settings, current_trial).
    """
    # TODO: between-subjects design
    # TODO: multi-session experiments
    def __init__(self, *args, **kwargs):
        """
        args: Variable instances
        kwargs: trials_per_type_per_block, blocks_per_type, trial_sort, block_sort, any number of variables = values
                output_names (column names in saved data)
        """
        self.output_names = kwargs.pop('output_names')
        trial_list_settings_defaults = {'trials_per_type_per_block': 1,
                                        'blocks_per_type': 1,
                                        'trial_sort': 'random',
                                        'block_sort': 'random'}
        self.trial_list_settings = {key: kwargs.pop(key, default)
                                    for key, default in trial_list_settings_defaults.items()}

        self.variables = list(args)
        for k, v in kwargs.items():
            self.variables.append(new_variable(k, v))

        self.trial_ivs = [v for v in self.variables if isinstance(v, IndependentVariable) and v.change_by == 'trial']
        self.block_ivs = [v for v in self.variables if isinstance(v, IndependentVariable) and v.change_by == 'block']
        self.constants = [v for v in self.variables if isinstance(v, ConstantVariable)]
        self.custom_vars = [v for v in self.variables if isinstance(v, CustomVariable)]

        self.n_blocks = 0
        self.n_trials = 0

        self.blocks = list(self.block_list(**self.trial_list_settings))
        self.raw_results = []

    def block_list(self, trials_per_type_per_block=1, blocks_per_type=1, trial_sort='random', block_sort='random'):
        # In this and the next block, we cross the indices of each IV's levels rather than the actual values.
        # This allows for subclasses to override the value method and do stuff besides indexing to determine the value.
        if self.trial_ivs:
            iv_idxs = itertools.product(*[range(len(v)) for v in self.trial_ivs])
            trial_types = [{iv.name: iv.value(condition[idx]) for idx, iv in enumerate(self.trial_ivs)}
                           for condition in iv_idxs]
        else:
            trial_types = [{v.name: v.value for v in self.variables if v not in self.block_ivs}]

        if self.block_ivs:
            iv_idxs = itertools.product(*[range(len(v)) for v in self.block_ivs])
            block_types = [{iv.name: iv.value(condition[idx]) for idx, iv in enumerate(self.block_ivs)}
                           for condition in iv_idxs]
        else:
            block_types = [{}]

        # TODO: Pass any args/kwargs to custom_vars.value?
        more_vars = lambda idx: {v.name: v.value() for v in np.concatenate((self.custom_vars, self.constants))}

        # Constructing sort functions, rather than directly sorting, allows for a different sort for each call
        sort_block = make_sort_function(trial_types, trials_per_type_per_block, trial_sort)
        sort_session = make_sort_function(block_types, blocks_per_type, block_sort)

        blocks = list(sort_session())
        self.n_trials = len(blocks) * len(sort_block())
        self.n_blocks = len(blocks)
        for block_idx, block in enumerate(blocks):
            trials = list(sort_block())
            for trial_idx, trial in enumerate(trials):
                # Add block-specific IVs, custom vars, and constants
                trial.update({k: v for k, v in block.items()})
                trial.update(more_vars(block_idx*len(trials) + trial_idx))
            yield pd.DataFrame(trials, index=block_idx*len(trials) + np.arange(len(trials)))

    def save_data(self, output_file):
        """
        Trial settings and results are combined into one DataFrame, which is pickled.
        """
        # Concatenate trial settings
        trial_inputs = pd.concat(self.blocks)

        results = pd.DataFrame(self.raw_results, columns=self.output_names)

        pd.concat([trial_inputs, results], axis=1).to_pickle(output_file)

    def run_session(self, output_file):
        self.session_start()

        for block_idx, block in enumerate(self.blocks):
            if block_idx > 1:
                self.inter_block(block_idx, block)
            self.block_start(block_idx, block)

            for trial_idx, trial in block.iterrows():
                if trial_idx > 0:
                    self.inter_trial(trial_idx, **dict(trial))
                self.raw_results.append(self.run_trial(trial_idx, **dict(trial)))

            self.block_end(block_idx, block)
        self.session_end()

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