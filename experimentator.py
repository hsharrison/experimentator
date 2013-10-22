import numpy as np
import pandas as pd
import itertools
import functools
import warnings


def make_sort_function(array, n, method):
    if method == 'random':
        return functools.partial(np.random.permutation, n * array)
    #TODO: More sorts (e.g. counterbalance)
    elif len(method) == len(array):
        try:
            return lambda: n * array[method]
        except ValueError:
            warnings.warn('Unrecognized sort method {}.'.format(method), stacklevel=2)
            return make_sort_function(array, n, None)
    else:
        return lambda: n * array


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
        self.n = len(levels)
        self.design = design
        if self.design == 'between':
            self.change_by = 'participant'
        else:
            self.change_by = change_by

    def value(self, idx, *args, **kwargs):
        return self.levels[idx]


class CustomVariable(Variable):
    def __init__(self, name, func):
        super(CustomVariable, self).__init__(name)
        self.func = func

    def value(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class RandomVariable(CustomVariable):
    def __init__(self, name, lower, upper):
        super(RandomVariable, self).__init__(name, lambda: (upper - lower)*np.random.random() + lower)


def new_variable(name, levels):
    if callable(levels):
        return CustomVariable(name, levels)
    elif len(levels) == 1:
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
        self.variables = list(args)
        for k, v in kwargs.items():
            self.variables.append(new_variable(k, v))

        self.trial_ivs = [v for v in self.variables if isinstance(v, IndependentVariable) and v.change_by == 'trial']
        self.block_ivs = [v for v in self.variables if isinstance(v, IndependentVariable) and v.change_by == 'block']

        self.blocks = []
        self.n_blocks = 0
        self.n_trials = 0

    def block_list(self, trials_per_type_per_block=1, blocks_per_block_type=1,
                   trial_sort='random', block_sort='random'):
        if self.trial_ivs:
            iv_idxs = itertools.product(*[v.levels for v in self.trial_ivs])
            trial_types = [{iv.name: iv.value(condition[idx]) for idx, iv in enumerate(self.trial_ivs)}
                           for condition in iv_idxs]
        else:
            trial_types = [{v.name: v.value for v in self.variables if v not in self.block_ivs}]

        if self.block_ivs:
            iv_idxs = itertools.product(*[v.levels for v in self.block_ivs])
            block_types = [{iv.name: iv.value(condition[idx]) for idx, iv in enumerate(self.block_ivs)}
                           for condition in iv_idxs]
        else:
            block_types = [{}]

        sort_block = make_sort_function(np.array(trial_types), trials_per_type_per_block, trial_sort)
        sort_session = make_sort_function(np.array(block_types), blocks_per_block_type, block_sort)

        blocks = list(sort_session())
        self.n_trials = len(blocks) * len(sort_block())
        self.n_blocks = len(blocks)
        for block in blocks:
            trials = list(sort_block())
            [trial.update({k: v for k, v in block.items()}) for trial in trials]
            yield pd.DataFrame(trials)

    def run_session(self, **kwargs):
        """
        kwargs: trials_per_type_per_block, blocks_per_block_type, trial_sort, block_sort
        """
        self.blocks = self.block_list(**kwargs)

        # TODO: initialize data

        self.session_start()
        for block_idx, block in enumerate(self.blocks):
            self.block_start(block_idx, block)
            for trial_idx, trial in block.iterrows():
                self.run_trial(trial_idx, **dict(trial))
                if trial_idx < len(block) - 1:
                    self.inter_trial(trial_idx, **dict(trial))
            self.block_end(block_idx, block)
            if block_idx < self.n_blocks - 1:
                self.inter_block(block_idx, block)
        self.session_end()

        #TODO: save data

    def run_trial(self, trial_idx, **kwargs):
        pass

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