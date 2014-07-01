.. _creation:

======================
Creating an experiment
======================

The typical workflow using experimentator is relatively straightforward:

1. Create an |Experiment| instance.
2. Run the experiment using the :ref:`CLI <cli>`.
3. Inspect, analyze or export the resulting data.

.. _constructors:

Constructor methods
===================

There are a number of ways to create an |Experiment|.

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
given the path to a file containing the specification in YAML format.

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
(either a Python dict or read from a YAML file via |Experiment.from_yaml_file|).
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
  you still have to call :meth:`Experiment.save() <experimentator.experiment.Experiment.save>`.

* Any remaining fields will be saved as a dictionary in |Experiment.experiment_data|.
  This is a good place to put local configuration that you read during a :ref:`callback <callbacks>`.

Using YAML
**********

All the nested lists and dictionaries required for |Experiment.from_dict| can be unwieldy.
An alternative is |Experiment.from_yaml_file|, which allows you to save your specification in an external file.
`YAML <http://en.wikipedia.org/wiki/YAML>`_ is a file-format designed to be both human- and computer-readable.

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

   filename: mixed_experiment.dat

The only new piece of information here is the filename.
It probably makes sense to include the filename in your YAML file,
so you have a  record of which data file is associated with the YAML file.

You can then create instantiate an |Experiment|, assuming the YAML above is stored in ``mixed_experiment.yaml``:

.. code-block:: python

   >>> from experimentator import Experiment
   >>> experiment = Experiment.from_yaml_file('mixed_experiment.yaml')

.. _from-scratch:

Constructing an Experiment from a DesignTree
--------------------------------------------

A final option for constructing an |Experiment| is to pass a |DesignTree| directly to the constructor.
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
   >>> experiment = Experiment(tree, filename='mixed_experiment.dat')

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
   ...     ivs=[
   ...         ('target_size', [10, 20, 30]),
   ...         ('target_speed', [5, 10, 20]),
   ...         ('target_position', None),
   ...     ],
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


:meth:`Design.get_order <experimentator.design.Design.get_order>` (usually called behind the scenes)
gives us a list of conditions, each a dictionary.
We can see here the correspondence between the design matrix and the conditions.
Because we used ``None`` with ``'target_position'``, its values are taken directly from the matrix.
For the other IVs, the values are taken from the list of possible values that we defined them with.

.. _callbacks:

Callbacks
=========

.. _contexts:

Context-managers
----------------
