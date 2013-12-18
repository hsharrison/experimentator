experimentator
==============

`experimentator` is a small Python module designed for running experiments in Python. The basic use case is that you have already written code to run a single trial and would like to run a set of experimental sessions in which inputs to your trial function are systematically varied and repeated.

Overview
-----
In `experimentator`, an `Experiment` is defined as a set of experimental sections arranged in a tree-like hierarchy. The default levels of the hierarchy are `('participant', 'session', 'block, 'trial')`. Each level can contain any number of sections on the level immediately below. An experiment might consist of 20 participants, each of which contains 2 sessions, each of which contains 4 blocks, etc. A simple experiment containing, for example, 1 block per session and 1 session per participant, could simplify the levels to `('participant', 'trial')`. Alternatively, different names altogether could be assigned to the levels.

 An independent variable (IV) is associated with a `kwarg` input of the function(s) that define a trial. If your `run_trial` function is declared as:

    def run_trial(self, target='center', congruent=True)

then your experiment has two IVs, one named `target` and the other named `congruent`. Of course, if you don't need to vary a `kwarg` input, you should rely on its default in the method declaration.

Traditionally, independent variables are categorized as varying over participants (in a _between-subjects_ design) or over trials (in a _within-subjects_ design). In reality however, a variable can be associated with any level. One variable may change every  trial, another may take on a new value only when the participant comes back for a second session.

If you would like some variables to have other behavior, for example to vary randomly, you should code this behavior in the `run_trials` method.

Usage
-----
First, create an `Experiment` instance objects, as so:

    my_experiment = Experiment(settings_by_level,
                    levels=('participant', 'session', 'block', 'trial'),
                    experiment_file='experiment.dat')

The positional argument is a mapping keyed on values of `levels`. The values are mappings keyed on `'ivs'`, `'sort'` and `'n'`. `ivs` is a mapping from independent variable names to a sequence of the possible values it can take. `sort` is a string (`random` currently the only option), or list of indices. `n` is the number of times each unique combination of IV values should appear at the associated level. These dictionaries aren't required to have an entry for each level. If there isn't an entry for any given level, that level will take the default behavior, which is no variables, `n = 1`, and no sort.

Finally, `experiment_file` is a location to save the experiment instance (so that additional sessions can be run after closing the Python interpreter).

You can also use a config file, creating an `Experiment` with:

    my_experiment = Experiment(config_file='config.ini',
                    experiment_file='experiment.dat')

See the section "Config file format" below for details.

Once you create your experiment, use it `run` method to decorate the function(s) that define your trial.

    @my_experiment.run
    def run_trial(self, target='center', congruent=True, **_):
        ...
        return {'reaction_time': rt, 'choice': response}

Any function(s) you decorate with `run` should return its results in the form of a dict. Every IV in the tree will be passed to the decorated function(s) as kwargs, including those used only at a higher level. This includes section numbers (e.g., `participant=2, block=1, trial=12`). For this reason, all decorated functions should include a kwarg wildcard input (`**_` here).

You can also define functions to run before, between, and after sections of your experiment, using the `start`, `inter`, and `end` methods as decorators. The only difference from the `run` method is that these decorators require a level name.

    @my_experiment.inter('trial')
    def short_pause(**_):
        time.sleep(1)

These functions will also be passed all IVs defined at their level or above (`inter` functions are passed the variables for the _next_ section), so the kwarg wildcard should be used here as well.

Example
---

    from experimentator import Experiment

    levels = ('experiment', 'participant', 'session', 'block', 'trial')
    settings = {'trial': dict(ivs={'target': ['left', 'center', 'right'],
                                  'congruent', [False, True]},
                              sort='random',
                              n=50),
                'participant': dict(ivs={'dual_task': [False, True]}),
                'block': dict(n=3)}
    my_experiment = Experiment(settings,
                               levels=levels,
                               experiment_file='my_experiment.dat')

    @my_experiment.run
    def run_trial(self, target='center', congruent=True, dual_task=False, **_):
        ...
        return dict(correct=correct, rt=rt)

    @my_experiment.start('session')
    def initialize_display(**_):
        ...

    @my_experiment.end('session')
    def close_display(**_):
        ...

    @my_experiment.inter('block')
    def offer_break(**_):
        ...

This experiment has a mixed design, with one between-subjects IV, `dual_task`, and two within-subjects IVs, `target` and `congruent`. Each session will have 150 trials, organized into 3 blocks. The `'session'` and `'block'` levels in this experiment are only organizational (as they have no associated variables) and facilitate calls to `initialize_display`, `close_display`, and `offer_break`.

Running a session (finally)
-------
The `experimentator` module has helper functions to work with experiments saved to disk. The easiest way to run a session is to use the helper function `run_experiment_section`. The following script will run a session for the first participant:

    from experimentator import run_experiment_section
    run_experiment_section('my_experiment.dat', participant=1)

Make sure to vary the kwarg here identifying which part of the experiment to run, or data will be overwritten (or configure your script such that the participant, session, etc. is a command line option). It is recommended to back up your experiment file before and after every session.
*Note: level numbers are indexed by 1, not by 0.*
You can pass more than one kwarg to `run_experiment_section`, for example if you are testing and would like to run only a single trial you could pass `trial=1`. Or if your experiment has multiple sessions per participant, you will have to specify the session number as well (or your script will run all the sessions back-to-back).

Other helper functions
----
If you change your mind and want to run more participants than you initially specified, you can use the `add_section` method:

    from experimentator import load_experiment

    my_experiment = load_experiment('my_experiment.dat')
    my_experiment.add_section(dual_task=True)
    my_experiment.save('my_experiment.dat')

If `dual_task=True` had not been specified, it would have been randomly chosen. Other `kwarg` inputs to `add_section` can determine where your new session is added. For example, if your experiment has a level `'group'` in between `'participant'` and `'session'`, you could specify `group=n` to add a new session under group `n`.

To handle custom quit events, e.g. pressing the `ESCAPE` key, raise the custom exception `QuitSession` in your `run_trial` method. Otherwise, ending the trial manually will start the next trial.

Finally, you can grab your data in a pandas DataFrame by accessing the `data` property. The data frame includes all the level numbers (indexed by 1) and IV values. Or, you can export directly to a comma-separated values file:

    from experimentator import export_experiment_data
    export_experiment_data('my_experiment.dat', 'my_experiment_data.csv')

Config file format
-------
    [Experiment]
    levels = comma-separated list
    sort methods = list, separated by commas or semicolons (for use when one or more sort method includes a comma)
    number = comma-separated list of integers

    [Independent Variables]
    variable name = level, comma- or semicolon-separated list of values

That is, each entry name in the Independent Variables section is interpreted as a variable name. The entry string is interpreted as a comma- or semicolon-separated. The first element should match one of the levels specified in the Experiment section. The other elements are the possible values (levels) of the IV. These values are interpreted by the Python interpreter, so proper syntax should be used for values that aren't simple strings or numbers.

Dependencies
------------

  * Python 3.3
  * Pandas 0.13 (still in development as of 12/17/2013)

License
-------

Copyright (c) 2013 Henry S. Harrison under the MIT license. See ``LICENSE.txt``.