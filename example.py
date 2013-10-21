import numpy as np

import experimentator as exp


class MyExperiment(exp.Experiment):
    """
    Example 'experiment' with two independent variables, one constant variable, and one random variable.
    """
    def run_trial(self, current_trial, **kwargs):
        return kwargs['iv1'] % kwargs['iv2'] + kwargs['cv'] + kwargs['rv']

    def session_start(self):
        print('Starting experiment...')

    def session_end(self):
        print('Experiment complete.')

    def inter_trial(self, current_trial, **kwargs):
        print('Moving to trial {}'.format(current_trial))


if __name__ == '__main__':
    # Create the experiment with 4 associated variables.
    experiment = MyExperiment(iv1=[4, 10], iv2=[0, 1, 2], cv=3, rv=np.random.random)
    # Cross the two independent variables.
    experiment.cross(['a', 'b'])
    # Randomize 8 trials of each type (total here: 8*6 = 48)
    experiment.randomize(8)
    # Run all 48 trials.
    experiment.run_session()