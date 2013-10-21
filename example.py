import numpy as np

import experimentator as exp


class MyExperiment(exp.Experiment):
    """
    Example 'experiment' with two independent variables, one constant variable, and one random variable.
    """
    def run_trial(self, current_trial, **kwargs):
        return kwargs['a'] % kwargs['b'] + kwargs['c'] + kwargs['d']

    def session_start(self):
        print('Starting experiment...')

    def session_end(self):
        print('Experiment complete.')

    def inter_trial(self, current_trial, **kwargs):
        print('Moving to trial {}'.format(current_trial))


if __name__ == '__main__':
    # Create the experiment with 4 associated variables.
    experiment = MyExperiment(a=[4, 10], b=[0, 1, 2], c=3, d=np.random.random)
    # Cross the two independent variables.
    experiment.cross(['a', 'b'])
    # Randomize 8 trials of each type (total here: 8*6 = 48)
    experiment.randomize(8)
    # Run all 48 trials.
    experiment.run_session()