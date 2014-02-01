<sub>_This project is hosted on both [bitbucket](https://bitbucket.org/hharrison/experimentator) and [github](https://github.com/hsharrison/experimentator). The bitbucket repository is considered canonical; however the github repository is almost always up-to-date. Issues can be tracked on either website, but github is preferred._</sub>

experimentator
==============

`experimentator` is a Python package for designing, constructing, and running experiments in Python. Its original purpose was for Psychology experiments, in which participants  interact with the terminal or, more commonly, a graphical interface, but there is nothing domain-specific; `experimentator` will be useful for any kind of experiment run with the aid of a computer. The basic use case is that you have already written code to run a single trial and would like to run a set of experimental sessions in which inputs to your trial function are systematically varied and repeated.

`experimentator` requires Python 3.3 or later. It is not Python 2.7-compatible (if you wish it to be, consider contributing your time to the project to make it happen). Additionally, it requires the third-party libraries `pandas` (v0.13.0 or later) to access experimental data, and `docopt` (0.6.1 or later) to use the command-line interface. The full install process, then is (assuming you are in a Python 3.3 virtualenv):

    pip install pandas>=0.13.0
    pip install docopt>=0.6.1

    hg clone https://bitbucket.org/hharrison/experimentator
    # or
    git clone https://github.com/hsharrison/experimentator

    cd experimentator
    python setup.py install


Overview
-----
In `experimentator`, an `Experiment` is defined as a set of experimental sections arranged in a tree-like hierarchy. The default levels of the hierarchy are `('participant', 'session', 'block, 'trial')`. Each level can contain any number of sections on the level immediately below. An experiment might consist of 20 participants, each of which contains 2 sessions, each of which contains 4 blocks, etc. A simple experiment containing, for example, 1 block per session and 1 session per participant, could simplify the levels to `('participant', 'trial')`. Alternatively, different names altogether could be assigned to the levels.

 An independent variable (IV) is associated with a `kwarg` input of the function(s) that define a trial. If your 'run' callback (explained below) is declared as:

    def run_trial(session_data, persistent_data, target='center', congruent=True)

then your experiment has two IVs, one named `target` and the other named `congruent`. Of course, if you don't need to vary a `kwarg` input, you should rely on its default in the method declaration.

Side note: All callbacks in `experimentator` receive dicts `session_data` and `persistent_data` as positional arguments. `session_data` is an empty dict every time you load the epxeriment from disk, but within an experimental session it is persistent. Use it to store experimental state, for example, a session score that persists from trial-to-trial. 'session' in `session_data` does not refer to the experiment section 'session', but rather a session of the Python interpreter. `persistent_data` is a place to store data that will persist over the course of the entire experiment. This is used, for example, to store data from the experiment's config file, if there is one (see section on config files below).

Traditionally, independent variables are categorized as varying over participants (in a _between-subjects_ design) or over trials (in a _within-subjects_ design). In reality however, a variable can be associated with any level. One variable may change every  trial, another may take on a new value only when the participant comes back for a second session.


Usage
-----
First, create an `Experiment` instance, as so:

    my_experiment = Experiment(config_file='config.ini',
                               experiment_file='experiment.dat')


`config_file` defines the structure of the experiment (syntax below), and `experiment_file` is a location to save the experiment instance (so that additional sessions can be run after closing the Python interpreter).

Once you create your experiment, assign a function as its 'run' callbakc to define a single trial.

    def run_trial(session_data, experiment_data, target='center', congruent=True, **_):
        ...
        return {'reaction_time': rt, 'choice': response}

    my_experiment.set_run_callback(run_trial)

The 'run' callback return its results in the form of a dict. Every IV in the tree will be passed to the decorated function(s) as kwargs, including those used only at a higher level. This includes section numbers (e.g., `participant=2, block=1, trial=12`). For this reason, all decorated functions should include a kwarg wildcard input (`**_` here).

You can also define functions to run before, between, and after sections of your experiment using the methods `set_start_callback`, `set_inter_callback`, and `set_end_callback`. The only difference from the `set_run_callback` method is that these methods also require the level name. For example:

    def short_pause(session_data, experiment_data, **_):
        time.sleep(1)

    my_experiment.set_inter_callback('trial', short_pause)

These functions will also be passed all IVs defined at their level or above (`inter` functions are passed the variables for the _next_ section), so the kwarg wildcard should be used here as well.


Config file format
-------
    [Experiment]
    levels = comma-separated list
    sort methods = names of sort methods, separated by commas
    number = comma-separated list of integers

    [Independent Variables]
    variable name = level, comma- or semicolon-separated list of values

In the `Experiment` section, all three lines should have the same number of items, separated by commas. The `levels` setting names the levels, the `sort methods` setting defines them (more on sort methods below), and the `number` setting specifies how many sections at this level to repeat, _per unique combination of IVs_. That is, in a 2x2 design with both IVs varying at the trials level, setting number to 10 for trials will generate an experiment with 40 trials per section.

Each setting in the `Independent Variables` section (that is, the name on the right of the `=`) is interpreted as a variable name. The entry string (to the left of the `=` is interpreted as a comma- or semicolon-separated list. The first element should match one of the levels specified in the Experiment section. This is the level to associate this variable with. The other elements are the possible values of the IV. These values are interpreted by the Python interpreter, so proper syntax should be used for values that aren't simple numbers (this allows your IVs to take on values of dicts or lists, for example). This means that values that are strings should be enclosed in quotes.

Other sections of the config file are saved as dicts in the experiment's `persistent_data` attribute. Fonts and colors are parsed according to the formats below, and are identified as either appearing in their own sections 'Fonts' and 'Colors' are on their own line with the label 'font' or 'color'. Everything else will be parsed as strings, so it is up to you to change types on elements of `persistent_data` after your experiment instance is created.

Colors are three integers separated by commas, and fonts are a string and then an integer. For example:

    [Colors]
    white = 255, 255, 255
    black = 0, 0, 0

    [Fonts]
    title = Times, 48
    text = Monaco, 12

    [Score]
    color = 255, 0, 255
    font = Garamond, 24
    points_to_win = 100

This example will produce the following `persistent data`:

    {'colors': {'white': (255, 255, 255), 'black': 0, 0, 0},
     'fonts': {'title': ('Times', 48), 'text': ('Monaco', 12)},
     'score': {'color': (255, 0, 255), 'font': ('Garamond', 24), 'points_to_win': '100'},
    }

Note that all section names are transformed to lowercase.


A more complete example
---

`config.ini`:

    [Experiment]
    levels = participant, block, trial
    sort methods = random, random, random
    number = 12, 3, 50

    [Independent Variables]
    target = trial, 'left', 'center', 'right'
    congruent = trial, False, True
    dual_task = participant, False, True


`dual_task.py`:

    from experimentator import Experiment

    def run_trial(session_data, experiment_data, target='center', congruent=True, dual_task=False, **_):
        # Code that works the display and records response.
        return dict(correct=correct, rt=rt)

    def initialize_display(session_data, experiment_data, **_):
        # Code that sets up the display.

    def close_display(session_data, experiment_data, **_):
        # Code that closes the display.

    def offer_break(session_data, experiment_data, **_):
        # Code that gives an opportunity to take a break.


    if __name__ == '__main__':
        dual_task_experiment = Experiment(config_file='config.ini',
                                          experiment_file='dual_task.dat')
        dual_task_experiment.set_run_callback(run_trial)
        dual_task_experiment.set_start_callback('participant', initialize_display)
        dual_task_experiment.set_inter_callback('block', offer_break)
        dual_task_experiment.set_end_callback('participant', close_display)
        dual_task_experiment.save()

This experiment has a mixed design, with one between-subjects IV, `dual_task`, and two within-subjects IVs, `target` and `congruent`. Each session will have 150 trials, organized into 3 blocks. The `'block'` level in this experiment is only organizational (as it has no associated IVs) and merely facilitate calls to `offer_break`.

The technique of only creating the experiment instance in the `if __name__ == '__main__'` block is important, because later when you run a participant, `experimentator` will import `dual_task_experiment.py` to reload the callback functions. If `my_experiment.save()` is called during this reloading, it risks overwriting the original data file. Only calling `python dual_task.py` will create an experiment file (`dual_task.dat` in this case--but note that the file extension is irrelevant).


Running a session (finally)
-------

The `experimentator` module has a clean command-line interface for running sections from an already-created experiment. You must use the `-m` flag to tell python to access the package's command-line interface. Here the syntax, the output of `python -m experimentator --help`:

    Usage:
      experimentator run <experiment_file> (--next <level>  [--not-finished] | (<level> <n>)...) [--demo] [--debug]
      experimentator  export <experiment_file> <data_file> [--debug]
      experimentator -h | --help
      experimentator --version


    Commands:
      run <experiment_file> --next <level>      Runs the first <level> that hasn't started. E.g.:
                                                  experimentator.py run experiment1.dat --next session

      run <experiment_file> (<level> <n>)...    Runs the section specified by any number of level=n pairs. E.g.:
                                                  experimentator.py run experiment1.dat participant 3 session 1

      export <experiment_file> <data_file>      Export the data in <experiment_file> to csv format as <data_file>.
                                                  Note: This will not produce readable csv files for experiments with
                                                        results in multi-element data structures (e.g., timeseries, dicts).

    Options:
      --not-finished     Run the next <level> that hasn't finished.
      --demo             Don't save data.
      --debug            Set logging level to DEBUG.
      -h, --help         Show this screen.
      --version          Print the installed version number of experimentator.


To continue the example above, you could run an experiment by calling `python -m experimentator run dual_task.dat --next participant`. Or, if something goes wrong and you want to re-run a particular participant, you could run `python -m experimentator run dual_task.dat participant 1`.

Note that you must execute these commands from a directory containing _both_ the data file (`dual_task.dat` in this example) _and_ the original script (`dual_task.py`).


Sort methods
-----

Coming soon!


License
-------

Copyright (c) 2013-2014 Henry S. Harrison under the MIT license. See ``LICENSE.txt``.
