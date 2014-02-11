.. _command-line:

======================
Command-line interface
======================

``experimentator`` has a command-line interface for easily running sections of an already-created experiment. You must use the ``-m`` flag to tell python to access the package's command-line interface. Here is the syntax, the output of ``python -m experimentator --help`` (assuming you are in a Python 3.3 virtual environment):

.. automodule:: __main__

To continue the example from the previous section, you could run a participant by running, in the system shell: ::

    python -m experimentator run dual_task.dat --next participant

Or, if something goes wrong and you want to re-run a particular participant (note: this could overwrite data--although the experiment file will be automatically backed up), you could run: ::

    python -m experimentator run dual_task.dat participant 1

These commands must be executed from a directory containing *both* the experiment file (``dual_task.dat`` in this example) and the original script (``dual_task.py``). (To be more precise, the command-line option should point to the experiment file's relative or absolute location, and the original script must be on the Python path and importable as its original name)

It is recommended that you create an alias for ``python -m experimentator``. In Ubuntu, for example, add the following line to ``~/.bash_aliases`` (create it if it doesn't exist): ::

    alias exp='python -m experimentator'

Thereby allowing you to run a participant by running: ::

    exp run dual_task.dat --next participant

Finally, you can export data into ``.csv`` format by running: ::

    exp export dual_task.dat data.csv

Note that if you have compound data structures in your results (e.g., lists, dictionaries, etc.), the ``.csv`` file may not be readable. In this case it would be desirable to access the :meth:`Experiment.data` property manually and analyze your data from there.

Exiting gracefully
==================

In most cases, if an exception is encountered while running an experiment, the data produced during that session could be considered untrustworthy; after all, the code behaved in an unexpected manner. However, sometimes it is desirable to force a *controlled* exit from an experimental session even when things are working properly. To that end, ``experimentator`` provides a :class:`QuitSession` exception. Raise this exception when you wish to exit your Python session in a controlled manner. In this case, ``experimentator`` will save any accumulated data. Of course, you don't have to use this data; instead you could re-run the session.

If you wish to catch other errors, use a :ref:`context manager <contextmanagers>`.