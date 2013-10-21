import numpy as np
import pandas as pd


class Experiment():
    """
    Experiments should subclass this and override, at minimum, the method run_trial(settings).
    """
    def __init__(self, **kwargs):
        self.settings = [kwargs]

    def set_iv(self, name, levels, vary_over='trial'):
        pass

    def set_custom(self, name, fcn):
        pass

    def cross(self):
        pass

    def randomize(self, vary_over):
        pass

    def run_session(self):
        self.session_start()
        for i, t in enumerate(self.settings):
            self.run_trial(t)
            if i != len(self.settings):
                self.inter_trial(t)
        self.session_end()

    def run_trial(self, settings):
        pass

    def session_start(self):
        pass

    def session_end(self):
        pass

    def inter_trial(self):
        pass