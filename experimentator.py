class Experiment():
    def __init__(self, **kwargs):
        self.n = kwargs.pop('n', 1)
        self.settings = kwargs

    def set_iv(self, name, levels, vary_over='trial'):
        pass

    def set_custom(self, name, fcn):
        pass

    def cross(self):
        pass

    def counterbalance(self, vary_over):
        pass

    def randomize(self, vary_over):
        pass

    def session(self):
        pass

    def block(self):
        pass

    def trial(self):
        pass

    def session_start(self):
        pass

    def session_end(self):
        pass

    def inter_trial(self):
        pass

    def block_start(self):
        pass

    def block_end(self):
        pass

    def inter_block(self):
       pass