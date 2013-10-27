experimentator
==============

``experimentator`` is a small Python module designed for running Psychology experiments in Python. The basic use case is that you have already written code to run a single trial and would like to run an entire experimental session in which inputs to your trial function are systematically varied and the outputs are saved to disk.

Usage
-----

(see ``example.py``)

**First**, subclass ``Experiment``:

  * Override, at minimum, the method ``run_trial(trial_idx, **trial_settings)`` with code for your trial. Inputs to ``run_trial`` should be kwargs with the exception of ``trial_idx``.

  * Also consider overriding ``inter_trial``, ``block_start``, ``block_end``, ``inter_block``, ``session_start``, and ``session_end``. For advanced behavior, such as persistent trial-to-trial states, you may have to override the ``__init__`` and/or ``save_data`` methods.

**Second**, create an instance of your new class:

  * Use the syntax ``my_experiment_instance = MyExperiment(*variables, output_names=[], **more_variables, **settings)``.
  * ``variables`` should be instances of ``Variable`` subclasses:
      * ``ConstantVariable(name, value)``: passed to ``run_trial`` as ``name=value``
      * ``IndependentVariable(name, levels, design='within', vary_by='trial')``: passed to ``run_trial`` as ``name=levels[idx]`` with varying ``idx``. ``design`` can be any of ``{'within', 'between'}``; ``vary_by`` can be any of ``{'trial`, 'block', 'session', 'participant'}``. ``design='between'`` is the same as ``vary_by='participant'``.
      * ``CustomVariable(name, fcn)``: passed to ``run_trial`` as ``name=fcn()``
      * ``RandomVariable(name, lower, upper)``: ``CustomVariable`` with ``fcn=lambda: lower + (upper-lower) * numpy.random.random()``
  * ``output_names`` is a list of strings to be used as column headers for outputs from ``run_trial``.
  * ``more_variables`` is an alternative syntax to create variables: ``name=value`` for a ``ConstantVariable``, ``name=levels`` for an ``IndependentVariable``, or ``name=function`` for a ``CustomVariable``.
  * ``settings`` can include the following:
      * ``trials_per_type_per_block`` (default=1)
      * ``blocks_per_type`` (default=1)
      * ``trial_sort`` (string or array of indices, default=``'random'``)
      * ``block_sort`` (string or array of indices, default=``'random'``)

**Third**, call ``my_experiment_instance.run_session(output_file)`` to run your experiment. All inputs (variables) and outputs (results) of ``run_trial`` are saved to a pickled pandas DataFrame as ``output_file``.

TODO
----

  * Support for between-subjects designs.
  * Support for multi-session designs.
  * More sort options (e.g. counterbalancing).

Dependencies
------------

  * Python3.3 (have not tested compatibility with other versions).
  * Numpy
  * Pandas

License
-------

Copyright (c) 2013 Henry S. Harrison under the MIT license. See ``LICENSE.txt``.