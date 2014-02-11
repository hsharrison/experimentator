.. _overview:

=====================
Overview and concepts
=====================

.. _structure:

Experiment structure
====================

In ``experimentator``, an experiment, in the form of a :class:`Experiment` instance, contains :class:`ExperimentSection` instances arranged in a tree-like hierarchy. A standard, complete hierarchy would be ``('participant', 'session', 'block, 'trial')``. For example, an experiment might consist of 20 participants, each of which contains 2 sessions, each of which contains 2 blocks, each of which contains 20 trials. You might visualize (part of) the tree of this experiment like this: ::

    experiment   base_section__________________________________________
                 |                                            \        \
    participant  1___________________________                  2____    ...
                 |                           \                 |     \
    session      1____________                2_________       1___   ...
                 |            \               |         \      |   \
    block        1_______      2_______       1_______   ...   1_   ...
                 | \  \  \     | \  \  \      | \  \  \        | \
    trial        1  2  3  ...  1  2  3  ...   1  2  3  ...     1  ...

A simple experiment containing, for example, 1 block per session and 1 session per participant, could simplify the levels to ``('participant', 'trial')`` (blocks and sessions are unnecessary with only one per level). Alternatively, different names altogether could be assigned to the levels. In this documentation, the terms *parent* and *children* will be used to refer to hierarchical relationships on the tree. Although the level names are not hardcoded in any way, this documentation will refer to sessions, blocks, trials, etc. for ease of communication.

**Important note:** when calling methods and functions in this library that refer to experiment sections by number, they are indexed starting at 1, as in the above chart. However, if interacting directly with :attr:`ExperimentSection.children` attribute (which will be done rarely), the standard Python convention of indexing starting at 0 is used, as this attribute is a list.

A design goal for ``experimentator`` is that each :class:`ExperimentSection` only knows how to handle its children, the sections immediately below it. A block knows how to create, order, and eventually run trials, but knows nothing of the higher levels of the hierarchy. The :class:`Experiment` instance exists mostly for convenience, to facilitate running :class:`ExperimentSection`s and retrieving data from them, among other things. In most cases, you will never need to interact directly with :class:`ExperimentSection`s.

In general, you will use ``experimentator`` by writing a script that constructs your experiment and saves it to disk. Then you can run your experiment using the :ref:`command-line interface <command-line>`.

Create an :class:`Experiment` like so:

.. code-block::

    from experimentator import Experiment

    my_experiment = Experiment(config_file='config.ini', experiment_file='experiment.dat')
    # Set callbacks (discussed below)
    my_experiment.save()

Note: the file extension on the ``experiment_file`` is meaningless. The file will be a binary file created by :mod:`pickle`.

.. _ivs:

Independent variables (IVs)
===========================

In human-subjects research, IVs are traditionally categorized as varying between participants (in a *between-subjects* design) or within each participant (in a *within-subjects* design). To be more specific, however, a variable can be associated with any level. An IV varying at the participant level would be considered a *between-subjects* variable; however, a *within-subjects* variable might take on a new value every trial, every block, or every session. In this way we can say that an IV belongs to one level or another. Each IV can take multiple values, defined in the experiment's :ref:`config file <config>`. At each level, if there are multiple IVs at a level, their values are crossed to create unique *conditions*, and these conditions are duplicated and ordered according to the level's :ref:`ordering method <orderings>`.

Each IV is associated with a keyword argument to the primary function in an experiment, the function that defines one run of the lowest level of the hierarchy (i.e., one trial). This function is called the *run* :ref:`callback <callbacks>`.  For example, consider the following function:

.. code-block::

    def run_trial(session_data, experiment_data, *, target, congruent, **kwargs):
        # Present stimuli, record data
        return {'reaction time': rt, 'choice': response}

Ignoring the :ref:`positional arguments <callback-args>` for now, this experiment would contain two IVs, named ``target`` and ``congruent``. In addition, there may be more wrapped up in the ``**kwargs`` expansion; more on this :ref:`below <callback-args>`. (The ``*,`` syntax in the argument list simply separates positional-only arguments from keyword-only arguments. This allows having the keyword arguments ``target`` and ``congruent`` without specifying a default).

The return values from the run callback define the experiment's *dependent variables* (DVs). They will be automatically saved in the :attr:`ExperimentSection.context` attribute and can be conveniently accessed via the property :meth:`Experiment.data`.

.. _ callbacks

Callbacks
=========

You can set your run callback using :meth:`Experiment.set_run_callback`:

.. code-block::

    my_experiment.set_run_callback(run_trial)

You can also define functions to run before, between, and after sections of your experiment using the methods :meth:`Experiment.set_start_callback`, :meth:`Experiment.set_inter_callback`, and :meth:`Experiment.set_end_callback`. The only difference from the `set_run_callback` method is that these methods also require the level name. For example:

.. code-block::

    def short_pause(session_data, experiment_data, **_):
        time.sleep(1)

    my_experiment.set_inter_callback('trial', short_pause)

This will cause the function ``short_pause`` to run between every trial of the experiment.

*Note to Python experts: The syntax for setting callbacks may tempt you to use decorators. However, I assure you it won't work, due to the intricacies of pickling and unpickling the callback functions. If you have any ideas on how to make it work, I encourage you to try it out and submit a pull request if it works.*

.. _callback-args:

Callback arguments
==================

All callbacks in ``experimentator`` have the same signature: two positional arguments and many keyword arguments.

- ``session_data`` is a dictionary which persists over the course of a Python session ("session" in the variable name refers to a Python session, not to an experimental session, although these will often be identical). It is empty every time you load the experiment from disk, but within a session it is persistent. Use it to store experimental state, for example a session score that persists from trial-to-trial or perhaps objects that reference external sound or video files.

- ``experiment_data`` is a dictionary where you can store data that will persist over the course of the entire experiment. This is used automatically to store information read from the experiment's :ref:`config file <config>`. Do not manually store objects in ``experiment_data`` that aren't `picklable <http://docs.python.org/3.3/library/pickle.html#what-can-be-pickled-and-unpickled>`_ (e.g. ``ctypes``).

- **keyword arguments** corresponding to any IVs associated with the level of the callback, and any levels above. The run callback, since it is by definition associated with the lowest level, receives as input all IVs in the experiment hierarchy. In addition to IVs, callbacks are passed the section numbers, indexed starting from 1 (i.e.., ``**kwargs`` will include something like ``{'participant': 5, 'session': 1, 'block': 2, 'trial': 12`}``). For this reason, it is a good idea to include a wildcard keyword expansion like ``**kwargs`` or ``**_`` (the underscore is convention for variables you don't intend to use) in your callback definitions. This will ensure Python won't raise an exception when it encounters an unexpected keyword argument.

.. _contextmanagers:

Context managers
================

You can also use Python's `context manager <http://docs.python.org/3.3/library/contextlib.html>`_ objects instead of, or in addition to, start and end callbacks, to define behavior that occurs at the beginning and end of every section at a particular level. You may be familiar with context managers as functions that are typically used in Python's `with statement <http://docs.python.org/3.3/reference/compound_stmts.html#with>`_).

Context managers have two advantages over start and end callbacks. First, they can return values. In a traditional ``with`` statement, the return variable is specified using the ``as`` keyword. In ``experimentator``, return values are stored in the ``session_data`` dictionary that is passed to other callbacks. Second, you can use a `try statement <http://docs.python.org/3.3/reference/compound_stmts.html#try>`_ in your context manager to ensure that some code (that would otherwise be in an end callback) executes even if an exception is raised while running the section.

The easiest way to create a context manager is with the :func:`contextlib.contextmanager` decorator. Then, attach the context manager to the :class:`Experiment` instance using the :meth:`Experiment.set_contextmanager` method:

.. code-block::

    from contextlib import contextmanager

    screen = get_screen()  # An made-up function to demonstrate passing
                           # an argument to set_contextmanager.

    @contextmanager
    def session_context(screen):
        window = open_window(screen)  # A made-up example function.

        try:
            yield window

        finally:
            window.close()


    my_experiment.set_contextmanager('session', session_context, screen)
    my_experiment.save()


To explain:
* Any code before the ``yield`` statement is executed before the section is run. This is the equivalent of a start callback.
* The ``yield`` statement marks where the section will be run. It is not necessary to yield any variables, but if you do, they are available to other functions as ``session_data['as'][level]``. In this example, the variable ``window`` can be accessed in callbacks by ``session_data['as']['session']``.
* Any code after the ``yield`` statement is executed after the section is run, the equivalent of an end callback.
* Use a ``try``/``finally`` statement to ensure code will be run in the case of an exception occurring. Any code in a ``finally`` block is executed after the section ends, or in case an exception is encountered during the ``try`` block. However, this isn't always necessary: if you don't have any code to run unconditionally, you can write a context manager without a ``try``/``finally`` statement.
* The method :meth:`Experiment.set_contextmanager` passes any extra positional or keyword arguments on to the given context manager.

For more on context managers, including other ways to create them, see :mod:`contextlib` in the standard library.

.. _together:

Putting it all together
=======================

A picture of an experiment should be emerging. When :func:`run an experiment section <run_experiment_section>`, ``experimentator`` descends the experiment tree, calling any start callbacks and opening any context managers along the way. When the bottom of the hierarchy is reached, the run callback is called and the return data is saved. On completing a section, its end callback is run, as is its inter callback if there is another section remaining on that level. If there is an open context manager associated with that section, it is closed before ``experimentator`` continues to the next section.

Any time along the way, the data can be accessed, as a :class:`pandas.DataFrame`, using the :meth:`Experiment.data` property, or exported to ``csv`` format using :func:`export_experiment_data`.
