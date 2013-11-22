experimentator
==============

`experimentator` is a small Python module designed for running experiments in Python. The basic use case is that you have already written code to run a single trial and would like to run a set of experimental sessions in which inputs to your trial function are systematically varied and repeated.

Overview
-----
In `experimentator`, an `Experiment` is defined as a set of experimental sections arranged in a tree-like hierarchy. The default levels of the hierarchy are `('participant', 'session', 'block, 'trial')`. Each level can contain any number of sections on the level immediately below. An experiment might consist of 20 participants, each of which contains 2 sessions, each of which contains 4 blocks, etc. A simple experiment containing, for example, 1 block per session and 1 session per participant, could simplify the levels to `('participant', 'trial')`. Alternatively, different names altogether could be assigned to the levels.

 An independent variable (IV) is associated with a `kwarg` input of the experiment's `run_trial` method. For instance, if your `run_trial` method is declared as:

    def run_trial(self, target='center', congruent=True)

then your experiment has two IVs, one named `target` and the other named `congruent`. Of course, if you don't need to vary a `kwarg` input, you can rely on its default in the method declaration.

Traditionally, independent variables are categorized as varying over participants (in a _between-subjects_ design) or over trials (in a _within-subjects_ design). In reality however, a variable can be associated with any level. One variable may change every  trial, another may take on a new value only when the participant comes back for a second session.

If you would like some variables to have other behavior, for example to vary randomly, you should code this behavior in the `run_trials` method.

Usage
-----
Your experiment should be written as a subclass of the `Experiment` class, overriding the following methods:

  * `run_trial(**kwargs)`
  * `start(level, **kwargs)`
  * `inter(level, **kwargs)`
  * `end(level, **kwargs)`

Overriding `run_trial` is required, the rest are optional and allow you to run commands before, between, or after any level of your experiment. Use an `if...elif` construct keyed on `level` to associate different `start`, `inter`, or `end` behavior with different levels of your experiment. For example, you may want to initialize the display at the beginning of each session in the call to `start('session', **kwargs)` or prompt the participant to take a break in the call to `inter('block', **kwargs)`. The `kwargs` for these methods are all determined from the same set of variables (the `kwargs` to the `inter` method are those associated with the _next_ section); they also include the section numbers, for example `..., participant=3, block=1, trial=18, ...` (indexed by 1).

The `Experiment` subclass you've now written is agnostic to organization of the IVs it takes. These are determined when you create an instance of your subclass, as so:

    my_experiment_instance = MyExperimentSubclass(settings_by_level,
                                                  levels=('participant', 'session', 'block', 'trial'),
                                                  experiment_file=None)

The positional argument is a mapping keyed on values of `levels`. The values are mappings keyed on `'ivs'`, `'sort'` and `'n'`. `ivs` is a mapping from independent variable names to a sequence of the possible values it can take. `sort` is a string (`random` currently the only option), or list of indices. `n` is the number of times each unique combination of IV values should appear at the associated level.

These dictionaries aren't required to have an entry for each level. If there isn't an entry for any given level, that level will take the default behavior, which is no variables, one repeat, and no sort.

Finally, `experiment_file` is a location to save the experiment instance (so that additional sessions can be run after closing the Python interpreter).

Example
---

    from experimentator import Experiment


    class MyExperiment(Experiment):
        def start(self, level, **_):
            if level == 'session':
                self.initialize_display()

        def end(self, level, **_):
            if level == 'session':
                self.close_display()

        def inter(self, level, **_):
            if level == 'block':
                self.offer_break()

        def run_trial(self, target='center', congruent=True, dual_task=False):
            ...
            return dict(correct=correct, rt=rt)

        def initialize_display(self):
            ...

        def close_display(self):
            ...

        def offer_break(self):
            ...


    levels = ('experiment', 'participant', 'session', 'block', 'trial')
    settings = {'trial': dict(ivs={'target': ['left', 'center', 'right'],
                                  'congruent', [False, True]},
                              sort='random',
                              n=50),
                'participant': dict(ivs={'dual_task': [False, True]}),
                'block': dict(n=3)}
    my_experiment = MyExperiment(settings,
                                 levels=levels,
                                 experiment_file='my_experiment.dat')

This experiment has a mixed design, with one between-subjects IV, `dual_task`, and two within-subjects IVs, `target` and `congruent`. Each session will have 150 trials, organized into 3 blocks. The `'session'` and `'block'` levels in this experiment are only organizational (as they have no associated variables) and facilitate calls to `initialize_display`, `close_display`, and `offer_break`.

Running a session (finally)
-------
The `experimentator` module has helper functions to work with experiments saved to disk. The easiest way to run a session is to use the helper function `run_experiment_section`. The following script will run a session for the first participant:

    from experimentator import run_experiment_section

    run_experiment_section('my_experiment.dat', participant=1)

Make sure to vary the kwarg here identifying which part of the experiment to run, or data will be overwritten (or configure your script such that the participant, session, etc. is a command line option). It is recommended to back up your experiment file before and after every session.
*Note: level numbers are indexed by 1, not by 0.*
You can pass more than one kwarg to `run_experiment_section`, for example if you are testing and would like to run only a single trial you could pass `trial=1`. Or if your experiment has multiple sessions per participant, you will have to specify the session number as well (or your script will run all the sessions back-to-back).

Other features
----
If you change your mind and want to run more participants than you initially specified, you can use the `add_section` method:

    from my-module import MyExperimentSubclass

    my_experiment = MyExperimentSubclass.load_experiment('my_experiment.dat')
    my_experiment.add_section(dual_task=True)
    my_experiment.save('my_experiment.dat')

If `dual_task=True` had not been specified, it would have been randomly chosen. Other `kwarg` inputs to `add_section` can determine where your new session is added. For example, if your experiment has a level `'group'` in between `'participant'` and `'session'`, you could specify `group=n` to add a new session under group `n`.

To handle custom quit events, e.g. pressing the `ESCAPE` key, raise the custom exception `QuitSession` in your `run_trial` method. Otherwise, ending the trial manually will start the next trial.

Finally, you can grab your data in a pandas DataFrame by accessing the `data` property. The data frame includes all the level numbers (indexed by 1) and IV values. Or, you can export directly to a comma-separated values file:

    from experimentator import export_experiment_data

    export_experiment_data('my_experiment.dat', 'my_experiment_data.csv')

Dependencies
------------

  * Python 3.3
  * Pandas 0.13 (still in development as of 11/6/2013)

License
-------

Copyright (c) 2013 Henry S. Harrison under the MIT license. See ``LICENSE.txt``.