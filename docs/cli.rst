.. _cli:

======================
Command-line interface
======================

You've generated your experiment, now what?
A major feature of experimentator is that it automatically turns your experiment into a command-line program,
via the command ``exp``.
The general format for running experimentator commands is::

    exp COMMAND <exp-file> OPTIONS

The available commands are :ref:`run-command`, :ref:`resume-command`, and :ref:`export-command`.
Additionally, ``exp --help`` (or ``-h``) will show the usage information,
and ``exp --version`` will print experimentator's version number.

.. _commands:

Commands
========

Here is the abridged usage message:

.. include:: ../src/experimentator/__main__.py
   :start-line: 3
   :end-before: Run/resume options:
   :literal:

Don't fear, an in-depth explanation follows.

.. _run-command:

run
---

The central command is ``run``.
There are a few ways to call it.

run --next
**********

To run the first section at ``<level>`` that hasn't been started::

    exp run <exp-file> --next <level>

For example, to run the next participant from ``example.exp``::

    exp run example.exp --next participant

To run the next participant that hasn't been *finished*
(as opposed to the next that hasn't *started*, the default)::

    exp run example.exp --next participant --not-finished


run <level> <n>
***************

To run a specific section::

    exp run <exp-file> (<level> <n>)...

The elipsis means that the previous element (the pair ``<level> <n>``)
can be repeated any number of times.
For example, to run the second session of the third participant::

    exp run example.exp participant 3 session 2

run --from
**********

In either version of ``run``, you can add the ``--from <n>`` option
to start at a specific section.
For example, to run the second session of the third participant,
starting at the second block::

    exp run example.exp participant 3 session 2 --from 2

``<n>`` can also be a comma-separated list of integers.
To start at the fourth trial of the second block::

    exp run example.exp participant 3 session 2 --from 2,4

``--from=<n>`` works the same as the ``from_section`` parameter to |run_experiment_section|;
see documentation for that method for details.

run options
***********

Here is the full set of options for the ``run`` command:

.. include:: ../src/experimentator/__main__.py
   :start-after: Run/resume options:
   :end-before: Export options

.. _resume-command:

resume
------

``resume`` is similar to ``run``.
There is nothing ``resume`` can do that ``run`` cannot, but ``resume`` makes resuming interrupted session easier.
There are two ways to call it.

If you only pass a level,
experimentator will try to resume the first section at that level that has been started but not finished.
The syntax is::

    exp resume <exp-file> <level>

For example, to resume the first block that has been started but not finished::

    exp resume example.expblock

One can also use specific section numbers with ``resume``::

    exp resume <exp-file> (<level> <n>)...

The specified section must have been started but not finished.
For example::

    exp resume example.expparticipant 3 session 2

The difference between the above example and using ``run`` is that with ``resume``,
experimentator will automatically start at the appropriate place;
with ``run``, experimentator will start at the beginning of the section
(unless an explicit starting point is passed with ``--from``).

``resume`` takes the same ``options`` as ``run``.

.. _export-command:

export
------

``export`` generates a text file with the experiment's data.
Its basic syntax is::

    exp export <exp-file> <data-file>

This one should be straightforward, but here is an example anyway::

    exp export example.expexample.csv

Its associated options:

.. include:: ../src/experimentator/__main__.py
   :start-after: Export options (see pandas.DataFrame.to_csv documentation):
   :end-before: Other options:

See :meth:`pandas.DataFrame.to_csv` for details on these options.

.. note::

   If your experiment has any complex data structures (e.g., a timeseries for every trial),
   it is not recommended to use the ``export`` command, as this will create an unparseable mess.
   Instead, access your data programmatically through the |Experiment.dataframe| attribute.
