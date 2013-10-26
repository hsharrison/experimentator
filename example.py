#!/usr/bin/python3.3
import experimentator as exp


class MyExperiment(exp.Experiment):
    """
    Example 'experiment' with two independent variables, one constant variable, and one random variable.
    """

    def run_trial(self, trial_idx, **kwargs):
        result = kwargs['iv1'] % kwargs['iv2'] + kwargs['cv'] + kwargs['rv']
        print('Trial {}: {}'.format(trial_idx, result))
        return result

    def session_start(self):
        print('Starting experiment...')

    def session_end(self):
        print('Experiment complete.')

    def inter_trial(self, trial_idx, **kwargs):
        print('Moving to trial {}'.format(trial_idx+1))


if __name__ == '__main__':
    # Create the experiment with 4 associated variables.
    experiment = MyExperiment(exp.RandomVariable('rv', 0, 1), iv1=[4, 10], iv2=[1, 2, 4], cv=3,
                              trials_per_type_per_block=8, output_names=['result'])
    # Randomize 8 trials of each type (total here: 8*6 = 48) and run all 48 trials.
    experiment.run_session('sample_results.pkl')