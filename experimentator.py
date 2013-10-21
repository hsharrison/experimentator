import numpy as np
import pandas as pd


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
    def __init__(self, name, levels):
        super(IndependentVariable, self).__init__(name)
        self.levels = levels
        self.n = len(levels)

    def value(self, idx, *args, **kwargs):
        return self.levels(idx)


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
    def __init__(self, variables, **kwargs):
        self.variables = variables
        for k, v in kwargs.items():
            self.variables.append(new_variable(k, v))

    def set_iv(self, name, levels, vary_over='trial'):
        pass

    def cross(self):
        pass

    def randomize(self, vary_over):
        pass

    def run_session(self):
        pass

    def run_trial(self, settings, current_trial):
        pass

    def session_start(self):
        pass

    def session_end(self):
        pass

    def inter_trial(self, settings, current_trial):
        pass