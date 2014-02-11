.. _example:

=======================
A more complete example
=======================


``config.ini``: ::

    [Experiment]
    levels = participant; block; trial
    orderings = Shuffle(6); Shuffle(3); Shuffle(10)

    [Independent Variables]
    target = trial; 'left'; 'center'; 'right'
    congruent = trial; False; True
    dual_task = participant; False; True


``dual_task.py``:

.. code-block::

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

This experiment has a mixed design, with one between-subjects IV, ``dual_task`` taking values ``(False, True)``, and two within-subjects IVs, ``target`` with values ``('left', 'center', 'right')``, and ``congruent`` with values ``(False, True)``. Each participant will have 180 trials, organized into 3 blocks. The blocks in this experiment are only organizational (as block has no associated IVs) and merely facilitate calls to ``offer_break``.

Avoiding overwriting the experiment file
========================================

The technique of only creating the experiment instance in a ``if __name__ == '__main__'`` block is important, because later when you run a participant, ``experimentator`` will import ``dual_task_experiment.py`` to reload the callback functions. If :meth:`Experiment.save` is called during this import, it risks overwriting the original data file. This way, the experiment file ``dual_task.dat`` will only be created when ``python dual_task.py`` is called directly. Note that after running an experimental session, the experiment file is automatically saved.
