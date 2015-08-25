.. _creation:

======================
Creating an experiment
======================

The typical workflow using experimentator is relatively straightforward:

1. Create an |Experiment| instance.
2. Run the experiment using the :ref:`command-line interface <cli>`.
3. Inspect, analyze or export the resulting data.

.. _constructors:

Constructor methods
===================

The `most general <from-scratch>`_ way to create an |Experiment| is to use |Experiment.new|, but
there are a number of other methods that may be easier for many use cases.

.. _simple-constructors:

Simple constructor methods
--------------------------

These methods construct |Experiment| instances based on common experimental designs.

* |Experiment.within_subjects|:
  Construct an experiment with levels |participant| and |trial|, and IVs only at the |trial| level.
  For example:

  .. code-block:: python

      >>> from experimentator import Experiment, order
      ... independent_variables = {
      ...     'side': ['left', 'right'],
      ...     'display_time': [0.1, 0.55, 1],
      ... }
      ... experiment = Experiment.within_subjects(
      ...     independent_variables,
      ...     n_participants=20,
      ...     ordering=order.Shuffle(10)
      ... )

  The above creates a 2 (side) by 3 (display time) within-subjects experiment,
  with 10 trials of each condition and 20 participants.
  Trials will be shuffled within participants.

* |Experiment.blocked|:
  Construct an experiment with levels |participant|, |block|, and |trial|,
  with IVs at the |trial| level (and optionally at the |block| level also).
  The following constructs an experiment identical to the previous example,
  except with each participant's 60 trials split into two blocks:

  .. code-block:: python

     >>> from experimentator import Experiment, order
     ... independent_variables = {
     ...     'side': ['left', 'right'],
     ...     'display_time': [0.1, 0.55, 1],
     ... }
     >>> experiment = Experiment.blocked(
     ...     independent_variables,
     ...     n_participants=20,
     ...     orderings={
     ...         'trial': order.Shuffle(5),
     ...         'participant': order.Ordering(2),
     ...     }
     ... )

  In the above example, it doesn't matter what ordering method we use at the |block| level;
  since there are no block-level IVs, all blocks are identical.
  We could, alternatively, introduce an IV at the block level:

  .. code-block:: python

     >>> from experimentator import Experiment, order
     ...  independent_variables = {
     ...     'side': ['left', 'right'],
     ...     'display_time': [0.1, 0.55, 1],
     ... }
     >>> experiment = Experiment.blocked(
     ...     independent_variables,
     ...     block_ivs={'difficulty': ['easy', 'hard']}
     ...     n_participants=20,
     ...     orderings={'trial': order.Shuffle(5)}
     ... )

  In this example, we introduced the IV ``'difficulty'`` with two levels.
  Since we didn't specify an ordering for blocks, ``Shuffle(1)`` will be used.
  In other words, each participant will experience one ``'easy'`` and one ``'hard'`` block, in a random order.


* |Experiment.basic|:
  Construct an experiment with arbitrary levels but a homogeneous structure.
  This constructor can handle any experimental structure, with the exception of :ref:`heterogeneity <heterogeneity>`.
  For example, to create the same blocked experiment as in the previous example:

  .. code-block:: python

     >>> from experimentator import Exeriment, order
     >>> independent_variables = {
     ...     'trial': {
     ...         'side': ['left', 'right'],
     ...         'display_time': [0.1, 0.55, 1],
     ...     },
     ...     'block': {'difficulty': ['easy', 'hard']},
     ... }
     >>> experiment = Experiment.basic(
     ...     ('participant', 'block', 'trial'),
     ...     independent_variables,
     ...     ordering_by_level={
     ...         'participant': order.Ordering(20),
     ...         'trial': order.Shuffle(5),
     ...     }
     ... )

  Again, the default ``Shuffle(1)`` will be used at the |block| level.

  We could also use |Experiment.basic| to make a mixed-design experiment,
  by adding a new IV at the |participant| level:

  .. code-block:: python

     >>> from experimentator import Exeriment, Shuffle
     >>> independent_variables = {
     ...     'trial': {
     ...         'side': ['left', 'right'],
     ...         'display_time': [0.1, 0.55, 1],
     ...     },
     ...     'block': {'difficulty': ['easy', 'hard']},
     ...     'participant': {'vision': ['monocular', 'binocular']},
     ... }
     >>> experiment = Experiment.basic(
     ...     ('participant', 'block', 'trial'),
     ...     independent_variables,
     ...     ordering_by_level={
     ...         'participant': Shuffle(20),
     ...         'trial': Shuffle(5),
     ...     }
     ... )

  In addition to adding the IV ``'vision'`` at the |participant| level,
  we also changed the |participant| ordering from |Ordering| to |Shuffle|
  in order to assign participants to conditions randomly.
  Note that we kept the ``number`` parameter on the |participant| ordering at 20;
  this means our experiment will now require 40 participants,
  since there will be 2 conditions at the |participant| level.

.. _spec-constructors:

Specification-based constructor methods
---------------------------------------

Experimentator provides a dictionary-based specification format for creating new |Experiment| instances.
There are two relevant constructor methods:
|Experiment.from_dict| constructs an |Experiment| given a dictionary, and
|Experiment.from_yaml_file| constructs an |Experiment|
given the path to a file containing the specification in `YAML`_ format.

The specification is the same for both.
Central to the specification format is specifying a |DesignTree| and its constituent |Design| instances.

.. _design-spec:

Design specification format
***************************

.. seealso::

   :ref:`designs`
       More information on the |Design| concept.

   |Design.from_dict|
       The method that implements the construction of a |Design| from a specification dictionary.

A single |Design| instance can be created from a dictionary
(either a Python dict or read from a `YAML`_ file via |Experiment.from_yaml_file|).
The dictionary can contain any of the following keys, all optional:

* ``'name'``:
  The name of the level.

* ``'ivs'``:
  The designs's independent variables.
  Can be a dictionary mapping IV names to possible IV values,
  or a list of ``(name, values)`` tuples.
  See :ref:`IVs`.
  If ``'ivs'`` is not specified, the design will have no IVs.

* ``'order'`` or ``'ordering'``:
  The design's ordering method.
  Can be specified in three ways:

    * as a string, interpreted as a class name in the :mod:`~experimentator.order` module;
    * as a dictionary, with the key ``'class'`` containing the class name
      and the rest of the items containing keyword arguments to its constructor; or
    * as a sequence, with the first item containing the class name
      and the rest of the items containing positional arguments to its constructor.

  If no ordering is specified, the default is |Shuffle|
  (|Ordering| if a :ref:`design matrix <design-matrices>` is used).

* ``'n'`` or ``'number'``:
  The ``number`` argument to the specified ordering class can be specified here
  (or as part of the ``ordering`` specification).

* ``'design_matrix'``:
  An array-like (e.g., a list of lists) specifying a design matrix to use at this level.
  See :ref:`design-matrices`.

* Any remaining fields are passed to the |Design| constructor as the ``extra_data`` argument.
  These values are associated with any sections created under this design.
  For example, you could pass ``{'practice': True}`` to practice blocks, to mark them as such.

For example, the following creates a |Design| instance
equivalent to the one at the |trial| level in the previous example (of |Experiment.basic|):

.. code-block:: python

   >>> from experimentator import Design
   >>> level_name, design = Design.from_dict(dict(
   ...     name='trial',
   ...     ivs={
   ...         'side': ['left', 'right'],
   ...         'display_time': [0.1, 0.55, 1],
   ...     },
   ...     ordering='Shuffle',
   ...     n=5,
   ... ))

For internal reasons, |Design.from_dict| outputs the level name as well as the |Design| object.
This shouldn't be too important,
because you will probably not be calling |Design.from_dict| directly,
but rather using the dictionary format within |Experiment.from_dict| or |Experiment.from_yaml_file|.

.. _design-tree-spec:

DesignTree specification format
*******************************

.. seealso::

   |DesignTree.from_spec|
     The method that implements this specification.

To create an |Experiment|, multiple |Design| instances are needed, collected under a single |DesignTree|.
This can also be done with a relatively simple specification format.

To create a |DesignTree| with a homogeneous structure, simply create a list of dictionaries,
each specifying the |Design| of one level, ordered from top to bottom.
For example, to create the |DesignTree| equivalent to the |Experiment.basic| mixed-design example above:

.. code-block:: python

   >>> from experimentator import DesignTree
   >>> tree = DesignTree.from_spec([
   ...     dict(name='participant',
   ...          ivs={'vision': ['monocular', 'binocular']},
   ...          n=20),
   ...     dict(name='block',
   ...          ivs={'difficulty': ['easy', 'hard']}),
   ...     dict(name='trial',
   ...          ivs={
   ...              'side': ['left', 'right'],
   ...              'display_time': [0.1, 0.55, 1]},
   ...          n=5),
   ... ])

This example takes advantage of the default ordering of |Shuffle| for all three levels.

A |DesignTree| can also be constructed with a list of ``(level_name, level_design)`` tuples,
though the specification format is more convenient as it can be used as part of the |Experiment| specification format.

Creating heterogeneous structures is a little more tricky;
it will be described :ref:`below <constructing-heterogeneity>`.

.. _experiment-spec:

Experiment specification format
*******************************

Once you can build a specification input suitable for |DesignTree.from_spec|,
constructing an |Experiment| is straightforward.
Create a dictionary with the following keys:

* ``'design'``:
  The |DesignTree| spec goes here (the list of dictionaries described above).
  This is the only required key.

* ``'file'`` or ``'filename'``:
  Use this field to associate your experiment with a data file.
  This is saved in the |Experiment.filename| attribute.
  Note that the |Experiment| will not be saved automatically;
  you still have to call :meth:`Experiment.save() <experimentator.Experiment.save>`.

* Any remaining fields will be saved as a dictionary in |Experiment.experiment_data|.
  This is a good place to put local configuration that you read during a :ref:`callback <callbacks>`.

Using YAML
**********

All the nested lists and dictionaries required for |Experiment.from_dict| can be unwieldy.
An alternative is |Experiment.from_yaml_file|, which allows you to save your specification in an external file.
`YAML`_ is a file-format designed to be both human- and computer-readable.

Porting the previous mixed-design example into a YAML file would look like this:

.. code-block:: yaml

   design:
     - name: participant
       ivs:
         vision: [monocular, binocular]
       n: 20

     - name: block
       ivs:
         difficulty: [easy, hard]

     - name: trial
       ivs:
         side: [left, right]
         display_time: [0.1, 0.55, 1]
       n: 5

   filename: mixed_experiment.exp

The only new piece of information here is the filename.
It probably makes sense to include the filename in your YAML file,
so you have a  record of which data file is associated with the YAML file.

You can then create instantiate an |Experiment|, assuming the YAML above is stored in ``mixed_experiment.yaml``:

.. code-block:: python

   >>> from experimentator import Experiment
   >>> experiment = Experiment.from_yaml_file('mixed_experiment.yaml')

.. note::

   This method is specifically for creating an |Experiment| from scratch.
   The data format used by |Experiment.save| for saving an in-progress experiment is also YAML,
   but using a different syntax, so it could be confused.
   This is why we recommend a different file suffix (our examples use ``.exp``).
   The in-progress experiment file with the ``.exp`` suffix will still contain YAML data,
   but it will be less likely to be confused with the YAML file passed to |Experiment.from_yaml_file|.
   
.. _from-scratch:

Constructing an Experiment from a DesignTree
--------------------------------------------

A final option for constructing an |Experiment| is to pass a |DesignTree|
directly to the general constructor |Experiment.new|.
For example, the following code would create the same |Experiment| as the previous example:

.. code-block:: python

   >>> from experimentator import DesignTree, Experiment
   >>> tree = DesignTree.from_spec([
   ...     dict(name='participant',
   ...          ivs={'vision': ['monocular', 'binocular']},
   ...          n=20),
   ...     dict(name='block',
   ...          ivs={'difficulty': ['easy', 'hard']}),
   ...     dict(name='trial',
   ...          ivs={
   ...              'side': ['left', 'right'],
   ...              'display_time': [0.1, 0.55, 1]},
   ...          n=5),
   ... ])
   >>> experiment = Experiment.new(tree, filename='mixed_experiment.exp')

.. _constructing-heterogeneity:

Constructing heterogeneous experiments
======================================

As we've noted, constructing a :ref:`heterogenous <heterogeneity>` |Experiment| is a bit more complicated.
To expand on the above example, let's imagine we want to create a two-session experiment.
The first session contains only one block, with only easy trials.
The second session will then contain an easy and a hard block.
Furthermore, we would like to add four practice trials at the beginning of each session.

Heterogeneity is created at the level of the |DesignTree|.
Remember how we built a |DesignTree| as a list of dictionaries?
To create a heterogeneous |DesignTree|, we need multiple lists of dictionaries.
We use a dictionary, where each value is a list of dictionaries
(specifying an internally homogeneous *section* of the tree),
and the keys give names to these sub-trees.

Experimentator will create the |DesignTree| by starting at the sub-tree with the key ``'main'``.
When it reaches the bottom of this sub-tree, it decides how to continue by looking for a special IV named ``'design'``.
If this IV exists, it uses its value to decide which sub-tree to use next.
When it reaches the end of these sub-trees, if there is an IV called ``'design'``
it again uses it to determine which sub-tree to use next.
If there is no IV called ``'design'``, then three tree ends.
In other words, the possible values of the ``'design'`` IV should be names of sub-trees.

For example, let's make our experiment more complex by adding practice trials and two different session types.
We'll add the practice trials by creating a new level called ``'section'``,
with the first section of each session proceeding to the practice trials, and the second into the experimental blocks.

We'll use the |Experiment.from_yaml_file| format:

.. literalinclude:: ../tests/doctest.yml
   :language: yaml

Now we have a complex, heterogeneous experiment.
Each participant will have two sessions;
each session will start with four practice trials
(a cross of two levels of the IV ``'side'``,
two levels of the IV ``'display_time'``,
and one level of the IV ``'easy'``).
The first session will include, after the practice section, sixty trials all with difficulty ``'easy'``.
The second session will include, after the practice session, two blocks in random order,
the first with difficulty ``'easy'`` and the second ``'hard'``, each with 30 trials.
To make this happen we created four sub-trees in addition to the ``'main`` tree.

Note that we added the custom key ``'practice'`` to the |trial| level,
to be able to more easily identify practice and experimental trials later
(Alternatively, we could separate them later by looking for trials with ``section==2``
and ignoring trials with ``section==1``).
Also note that we use the |Ordering| method to produce a predictable order of the sub-trees.
Otherwise, |Shuffle| is the default and we would get our sub-trees in a random order.
Sometimes this is what we want, however.
Because sub-trees are determined based on IV values, we can manipulate them in the same way as with other IVs,
with ordering methods, design matrices, and even crossing them with other "normal" IVs.

It is not necessary to have the same level names for all possible routes down the tree.
In this example, there are no blocks in the first session
(or the practice section of the second session, for that matter).
However, it is critical that all IVs get assigned a value in one place or another.
In this example, the only place that the IV ``'difficulty'`` can take the value ``'hard'``
is at the |block| level of the second session.
In other places on the design tree, we have to create an IV ``'difficulty'`` with only one level (``'easy'``)
to ensure that we never generate a trial without assigning a value to the IV ``'difficulty'``.

Manually modifying experiments
------------------------------

Another way to create complex experiment structures is to first construct a simple experiment,
then manually modify it.
For example, you can use the method |ExperimentSection.append_child| to add a child under any given section,
or |ExperimentSection.append_design_tree| to add an entire sub-tree.
See these methods' docstrings for details.
Be sure to call |Experiment.save| after to make the changes permanent.

.. _design-matrices:

Design matrices
===============

In all the examples so far, we've only specified possible IV values;
we let experimentator handle the creation of conditions of them.
Experimentator will use a full factorial cross, constructing a condition for every possible combination of IV values.
Sometimes this isn't what we want, though.
In a `fractional factorial design <http://en.wikipedia.org/wiki/Fractional_factorial_design>`_, for example,
only a subset of the possible combinations are used.
We can specify these, and other, designs in experimentator using
`design matrices <http://en.wikipedia.org/wiki/Design_matrix>`_.

The support for design matrices in experimenator is designed to be compatible with the Python library pyDOE_.
This is a library that allows for easy creation of various common design matrices.

Design matrices can be specified during the creation of |Design| objects.
This is the same place where IVs are specified when using the :ref:`spec-constructors`.

Each column of the design matrix is associated with one IV;
a design matrix should have the same number of columns as the number of IVs in the design at that level.
The order of IVs is important when using design matrices;
because dictionaries in Python have no inherent order,
|OrderedDict| should be used when defining IVs with design matrices,
or alternatively IVs can be specified as a list of tuples (see the |IV docs|).

Each row of the design matrix is one condition,
and the values of the matrix are interpreted in one of two ways:

* If the levels of an IV are passed as ``None`` rather than a list, then the IV is assumed to take arbitrary, continuous values.
  The values in the associated column of the design matrix are then interpreted at "face value".

* Otherwise, each value in the design matrix is interpreted as an index,
  determining which value to take from the list of possible IV values.
  Experimentator is smart about this and only cares about the relative value of these "indices".
  For example, if a design matrix column contains the values 0 and 1,
  they will be associated with the first and second IV values, respectively.
  Alternatively, if the column contains 1 and 2,
  then 1 will be associated with the first and 2 the second IV value.

A design matrix can also specify the order of conditions, by the order of its rows.
For this reason, the default ordering method is |Ordering| when a design matrix is used.
Change this to |Shuffle|, for example,
if you instead want the rows of the design matrix to appear in a random order.

Here is an example of using a `Box-Behnken design <http://pythonhosted.org/pyDOE/rsm.html>`_ with pyDOE_:

.. code-block:: python

   >>> import pyDOE
   >>> from experimentator import Design
   >>> design_matrix = pyDOE.bbdesign(3)
   >>> print(design_matrix)
   [[-1. -1.  0.]
    [ 1. -1.  0.]
    [-1.  1.  0.]
    [ 1.  1.  0.]
    [-1.  0. -1.]
    [ 1.  0. -1.]
    [-1.  0.  1.]
    [ 1.  0.  1.]
    [ 0. -1. -1.]
    [ 0.  1. -1.]
    [ 0. -1.  1.]
    [ 0.  1.  1.]
    [ 0.  0.  0.]
    [ 0.  0.  0.]
    [ 0.  0.  0.]]
   >>> trial_design = Design.from_dict(dict(
   ...     ivs=[('target_size', [10, 20, 30]),
   ...          ('target_speed', [5, 10, 20]),
   ...          ('target_position', None)],
   ...     design_matrix=design_matrix,
   ... ))
   >>> # The following is just to demonstrate the conditions that are created.
   >>> # These methods are usually called behind the scenes.
   >>> trial_design.first_pass()
   IndependentValue(name=(), values=())
   >>> trial_design.get_order()
   [{'target_position': 0.0, 'target_size': 10, 'target_speed': 5},
    {'target_position': 0.0, 'target_size': 30, 'target_speed': 5},
    {'target_position': 0.0, 'target_size': 10, 'target_speed': 20},
    {'target_position': 0.0, 'target_size': 30, 'target_speed': 20},
    {'target_position': -1.0, 'target_size': 10, 'target_speed': 10},
    {'target_position': -1.0, 'target_size': 30, 'target_speed': 10},
    {'target_position': 1.0, 'target_size': 10, 'target_speed': 10},
    {'target_position': 1.0, 'target_size': 30, 'target_speed': 10},
    {'target_position': -1.0, 'target_size': 20, 'target_speed': 5},
    {'target_position': -1.0, 'target_size': 20, 'target_speed': 20},
    {'target_position': 1.0, 'target_size': 20, 'target_speed': 5},
    {'target_position': 1.0, 'target_size': 20, 'target_speed': 20},
    {'target_position': 0.0, 'target_size': 20, 'target_speed': 10},
    {'target_position': 0.0, 'target_size': 20, 'target_speed': 10},
    {'target_position': 0.0, 'target_size': 20, 'target_speed': 10}]


:meth:`Design.get_order <experimentator.Design.get_order>` (usually called behind the scenes)
gives us a list of conditions, each a dictionary.
We can see here the correspondence between the design matrix and the conditions.
Because we used ``None`` with ``'target_position'``, its values are taken directly from the matrix.
For the other IVs, the values are taken from the list of possible values that we defined them with.

.. _callbacks:

Callbacks
=========

Up to this point, we've explained how to create an experiment of arbitrary complexity.
But presumably you actually something to happen when you run a trial.
This is accomplished with *callbacks*.
In general, a callback is a function that you supply that is automatically triggered at a certain time.
There are two types of callbacks in experimentator,
the :ref:`function callbacks <run-callback>` and :ref:`context-managers <contexts>`.
Both are set with |Experiment.add_callback|.

.. note::

   Be sure to save your experiment to disk after setting a callback, using |Experiment.save|,
   to make the changes permanent.

.. note::

   Experimentator does not store the callbacks with your |Experiment|, but rather
   every time you load your experiment, the callbacks are re-imported.
   Experimentator looks for a Python file with the same name as the functions were originally defined in.
   As a result, the data file exported by |Experiment.save| is not sufficient when you want to move an experiment
   between computers.
   You will also need to move the Python file(s) in which any callbacks are defined.

   |Experiment.add_callback| also takes optional keyword arguments
   ``func_name`` and ``func_module`` that you can set to tell experimentator where to look for the callback.

.. _run-callback:

Function callbacks
------------------

The most basic callbacks are function callbacks.
A function callback runs at the start of every section at its level.
Most commonly, this is used at the trial level to set the "trial function";
on other words, the behavior of every trial.

Callbacks should take two positional arguments.
It will be passed the current |Experiment| and |ExperimentSection| instances, respectively.
Everything that the run callback might need to know can be taken from these arguments.
Here are the most useful attributes:

* |ExperimentSection.data|:
  This is the |ChainMap| that contains the condition (IV values) for the currently running trial.
  It also includes the section numbers, for example ``section.data['trial']`` will get the current trial number.

* |Experiment.experiment_data|:
  This is a dictionary that you can use to store persistent data that every callback will have access to.
  By default, it is empty, but you can put data in here and it will always be available,
  even across sessions of the Python interpreter.
  This means that everything you put here must be |picklable|, so not everything will work.

* |Experiment.session_data|:
  This is where you can store data that is only persistent within the current session of the Python interpreter.
  Every time Python exits, this dictionary is emptied.
  This means you can store data here even if it is not |picklable|.
  This is the place to store external resources like multimedia data.
  You can reload these resources during a :ref:`context-manager callback <contexts>`.

The callback should return a dictionary, mapping dependent variable (DV) names to values.
The DV names are only used to label the columns in the final representation of the experiment's data,
|Experiment.dataframe|.

Set function callbacks using the |Experiment.add_callback| method.
You can also pass this method arbitrary positional and keyword arguments.
Therefore, the full signature for a callback is ``func(experiment, section, *args, **kwargs)``,
where ``func`` (the callback itself), ``*args``, and ``**kwargs``, are arguments to |Experiment.add_callback|.

.. _contexts:

Context-managers
----------------

The second type of callback is the context manager.
The name context manager is taken from the Python standard library, where they are referred to as |context-managers|
(the ``with`` statement is one way to *use* context managers,
but it is not generally used to *create* them).
Fundamentally, a context manager specifies behavior that should occur *before* something,
and behavior that should occur *after*.
In experimentator, the idea is that you will use context managers
to define behavior that occurs before, between, and after sections of the experiment.
One may want to open external resources (e.g., a sound file) at the beginning of each session,
and close them afterward, for example.
Another common use case would be to offer a break between blocks.

The most verbose way to create a context manager is to make a class that contains the magic methods
``__enter__`` and ``__exit__`` with "before" and "after" behavior, respectively.
See :ref:`typecontextmanager`.

A much more convenient way is to use the |contextlib.contextmanager| decorator in the standard library.
See the documentation for details, but it works like this:
first you code the "before" behavior, then the keyword ``yield``, then the "after" behavior.
Here is an example context manager that offers a break between blocks:

.. code-block:: python

   from contextlib import contextmanager

   @contextmanager
   def offer_break(experiment, section):
       # Don't need to offer a break before the first block.
       if section.data['block'] > 1:
           input('Take a break if you would like.\nPress ENTER when you are ready to continue.')

       yield
       print('Block {} completed.'.format(section.data['block']))


As you see, the signature of a context manager is the same as the signature of a function callback.
All the same data in the |Experiment| and |ExperimentSection| objects are also available to context managers.

.. note::

   In the above example, we could make the ``offer_break`` function work on any level of the experiment.
   Every |ExperimentSection| stores its level name in the attribute
   :attr:`~experimentator.section.ExperimentSection.level`.
   If we replace ``section.data['block']`` with ``section.data[section.level]``
   (we'd want to change the ``print`` message as well),
   then we could use ``offer_break`` at multiple levels.

Context-manager callbacks have the same signature as regular function callbacks, and are the added the same way.
The only exception is to pass the keyword argument ``is_context=True`` to |Experiment.add_callback|.

With both types of callback, pass the level name to |Experiment.add_callback|.
Continuing the previous example:

.. code-block:: python

   experiment.add_callback('block', offer_break, is_context=True)

If you are using the context manager to close resources,
it may be a good idea to use a try-finally block (see :ref:`tut-cleanup`)
to ensure that the resource is still closed in the case of an exception occurring.
Here is an example that loads audio using the library `pyglet <http://pyget.org>`_:

.. code-block:: python

   from contextlib import contextmanager
   import pyglet

   @contextmanager
   def load_audio(experiment, section):
       player = pyglet.media.Player()
       source = pyglet.media.load('background_music.mp3')

       # Make the Player available to other callbacks by saving it in session_data.
       experiment.session_data['player'] = player

       try:
           # Run the section.
           yield

       finally:
           # This block will run even if an error occurs during the try block.
           # If no error occurs, it will run after the section ends.
           player.delete()

.. note::

   This example is just for illustration.
   Pyglet is actually smart enough to delete ``player`` for you when the Python interpreter exits.

An alternative to manually editing |Experiment.session_data| is to put objects after the ``yield`` keyword.
Anything yielded by a context manager is stored in ``experiment.session_data[level_name]``
for the duration of the session.
In the above example, if we have ``yield player``, then we can access ``player`` from other callbacks
as ``experiment.session_data['session']``
(assuming ``load_audio`` is set as the context manager of the level |session|).
