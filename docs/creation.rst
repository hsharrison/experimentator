.. _creation:

======================
Creating an experiment
======================

The workflow using experimentator is relatively straightforward:

1. Create an :class:`~experimentator.experiment.Experiment` instance.
2. Run the experiment using the :ref:`cli <command-line interface>`.
3. Inspect, analyze or export the resulting data.

.. _structure:

Experiment structure
====================

In experimentator, experiments are organized as hierarchical *tree structures*.
Each section of the experiment (represented by an :class:`~experimentator.section.ExperimentSection` instance)
is a node in this tree, and its children are the sections it contains.
Levels on the tree are named;
common level names in behavioral research are ``'participant'``, ``'session'``, ``'block'``, and ``'trial'``.
For example, an experiment with two participants and three trials each would have a tree that looks like this::

    '_base'               ______1_____
                         /            \
    'participant'    ___1___        ___2___
                    /   |   \      /   |   \
    'trial'        1    2    3    1    2    3

The top level is always called ``'_base'``;
the leading underscore indicates that you should not have to refer to this level directly.
All other level names are arbitrary and are specified when the experiment is created.

.. note::
   For simplicity, this documentation uses the term *trial* to mean the lowest level of an experiment,
   even though experimentator will let you use whatever string you want for this name.

Be aware that experimentator uses 1-based indexing when numbering sections and indexing
:class:`~experimentator.section.ExperimentSection` instances, as illustrated in the diagram above.

.. _ IVs:

Independent variables
---------------------

A central concept in experimentator (and in experimental design more generally)
is that of *independent variables*, or IVs.
An IV is a variable that you are explicitly varying in order to test its effects.
The easiest way to represent IVs in experimentator is using a dictionary.
Each key is a string, the name of an IV.
Each value is either a list, representing the possible values the IV can take,
or ``None`` if the IV takes continuous values.
For example:

.. code-block:: python

    independent_variables = {
        'congruent': [True, False],
        'distractor': [None, 'left', 'right'],
        'difficulty': None,
    }

.. note::
   In Python, dictionaries have no order.
   In most cases, the order of IVs is not important and so representing IVs as dictionaries will work fine.
   However, there are times when the order you specify the IVs is important.
   This is the case, for example, when using a :ref:`design matrix`, because each column of the design matrix refers to one IV.
   You will need to rely on the order of IVs in order to know which column controls which IV.
   In these cases you should use one of two alternative ways of representing IVs:
   using a :class:`collections.OrderedDict`, or a list of 2-tuples.
   Here is an example of the latter method (equivalent to the previous example):

   .. code-block:: python

       independent_variables = [
           ('congruent', [True, False]),
           ('distractor', [None, 'left', 'right']),
           ('difficulty', None),
       ]

When you specify your IVs, you will specify them separately for every level of the experiment.
That is, every IV is associated with a level of the experimental hierarchy.
This determines how often the IV value changes.
For example, a within-subjects experiment will probably have IVs at the ``'trial'`` level,
a between-subjects experiment will have IVs at the ``'participant'`` level,
and a mixed-design experiment will have both.
An IV at the ``'participant'`` level will always take the same value within each participant.
Similarly, a blocked experiment will probably have IVs at the ``'block'`` level;
these IVs will only take on a new value when a new block is reached.

IV values are ultimately passed to your :ref:`run callback <callbacks>` as a *condition*.
A condition is a combination of specific IV values.
Although you don't need to create conditions yourself, you can think of them as dictionaries mapping IV names to values.
For example, a condition generated from the example IVs above might be

.. code-block:: python

    {'congruent': False,
     'distractor': None,
     'difficulty': 1.5}

.. _why levels:

Why use levels?
---------------

You may be wondering how many levels to use, or why to use them at all
(after all, `flat is better than nested`_).
That decision must be made on a case-by-case basis.
For example, imagine your experiment has sessions of 20 trials, divided into two blocks.
As long as the order of conditions within each session is correctly specified
(for example, by using a  :ref:`design matrix`),
using an explicit ``'block'`` level may not be necessary.
Alternatively, you could define a ``'block'`` level but not a ``'trial'`` level
and stick a trial loop inside the block.
However, using levels makes it possible to...

- associate an IV with a level, facilitating the creation and ordering of conditions.
- run code before and/or after every section at a particular level, using :ref:`section context managers <contexts>`.
  For example, offer participants a break between blocks.
- run experiment sections by level (using the :ref:`command-line interface <cli>`).
  For example, using blocks you could do

  ::

    exp run my_exp.dat participant 1 block 2

  rather than the more awkward

  ::

    exp run my_exp.dat participant 1 --from 11

- index the data by level, after running the experiment, using :ref:`hierarchical indexing <indexing.hierarchical>`.
  For example, to get the third trial of the first participant's second block you could do

  .. code-block:: python

      experiment.dataframe.loc[(1, 2, 3), :]

  or to get the first trial of the second block of every participant,

  .. code-block:: python

    data.xs((2, 1), level=('block', 'trial'))

.. _flat is better than nested: http://legacy.python.org/dev/peps/pep-0020/
