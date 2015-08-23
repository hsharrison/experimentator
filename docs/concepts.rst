.. _concepts:

========
Concepts
========

.. admonition:: About this documentation
   :class: Note

   This documentation aims to be comprehensive, but be aware that there is also rich information available in docstrings.
   These can be accessed at the interactive prompt with the ``help`` function;
   they are also reproduced in :ref:`api_reference`.

.. _structure:

Experiment structure
====================

In experimentator, experiments (represented by an |Experiment| instance) are organized as hierarchical tree structures.
Each section of the experiment (represented by an |ExperimentSection| instance)
is a node in this tree, and its children are the sections it contains.
Levels on the tree are named;
common level names in behavioral research are ``'participant'``, ``'session'``, ``'block'``, and ``'trial'``.
For example, an experiment with two participants with two blocks of three trials each would have a tree that looks like this::

   '_base'                       ______________1______________
                                /                             \
   'participant'         ______1______                   ______2______
                        /             \                 /             \
   'block'          ___1___         ___2___         ___1___         ___2___
                   /   |   \       /   |   \       /   |   \       /   |   \
   'trial'        1    2    3     1    2    3     1    2    3     1    2    3

The top level is always called ``'_base'``;
the leading underscore indicates that you should not have to refer to this level directly.
All other level names are arbitrary and are specified when the experiment is created.

An important principle of experimentator is that each section only handles its children,
the sections immediately below it.
In a structure with levels |participant|, |block|, and |trial|,
every block section knows how to create and order trials (e.g., by crossing :ref:`independent variables <IVs>`),
but knows nothing of participants.
Likewise, every participant section organizes the blocks under it,
but lets each block figure out its constitutent trials.
The only exception to this rule is in the case of :ref:`non-atomic orderings <non-atomic-orderings>`.

.. note::

   For simplicity, this documentation uses the term *trial* to mean the lowest level of an experiment,
   even though experimentator will let you use whatever string you want to name this level.

Navigating structure
--------------------

.. note::

   Be aware that experimentator uses 1-based indexing when numbering sections and indexing
   |ExperimentSection| instances, as in the diagram above.

An experimental hierarchy can be explored in a number of ways.
Given an |Experiment| object, any section can be found by direct indexing:

.. code-block:: python

   # Assuming the same structure as the diagram above.
   experiment[1]        # first participant
   experiment[1][2]     # second block of first participant
   experiment[1][2][2]  # second trial of second block of first participant
   experiment[1, 2, 2]  # same as previous

Alternatively, the :meth:`~experimentator.section.ExperimentSection.subsection` method can be used.
The following finds the same sections as the previous example:

.. code-block:: python

   experiment.subsection(participant=1)
   experiment.subsection(participant=1, block=2)
   experiment.subsection(participant=1, block=2, trial=2)

The generator method :meth:`~experimentator.section.ExperimentSection.all_subsections`
yields all subsections matching the given criteria.
For example, with the same experiment structure,

.. code-block:: python

   list(experiment.all_subsections(block=2, trial=1))

will return the same list as

.. code-block:: python

   [experiment.subsection(participant=1, block=2, trial=1),
    experiment.subsection(participant=2, block=2, trial=1)]

There are other methods to help find specific sections, for example
:meth:`~experimentator.section.ExperimentSection.find_first_not_run`,
:meth:`~experimentator.section.ExperimentSection.find_first_partially_run`,
and the more general
:meth:`~experimentator.section.ExperimentSection.depth_first_search` and
:meth:`~experimentator.section.ExperimentSection.breadth_first_search`.
These last two methods allow you to define the search criteria with a custom ``key`` function
that returns ``True`` for the desired section.

.. _designs:

Design
======

In experimentator, every section has a *design*, represented by a |Design| object
(usually, these will be created for you).
Most of the time, all sections at the same level have the same design
(but see :ref:`heterogeneity`).
The design is a high-level description of one level of an experiment.
It includes everything experimentator needs to know to create the children of a section.
This consists of two things:
:ref:`independent variables <IVs>` and an :ref:`ordering method <orderings>`.

An experiment requires multiple |Design| instances in a certain relationship to each other.
Such a collection is modeled with |DesignTree| objects.
Again, you usually will not manually create these.

.. _IVs:

Independent variables
---------------------

A central concept in experimentator (and in experimental design more generally)
is that of *independent variables*, or IVs.
An IV is a variable that you are explicitly varying in order to test its effects.
The easiest way to represent IVs in experimentator is using a dictionary.
Each key is a string, the name of an IV.
Each value is either a list, representing the possible values the IV can take,
or ``None`` if the IV takes continuous values (continuous values are only possible with a |design matrix|).
For example:

.. code-block:: python

   >>> independent_variables = {
   ...     'congruent': [True, False],
   ...     'distractor': [None, 'left', 'right'],
   ... }

.. note::
   In Python, dictionaries have no order.
   In most cases, the order of IVs is not important and so representing IVs as dictionaries will work fine.
   However, there are times when the order you specify the IVs is important.
   This is the case, for example, when using a |design matrix|, because each column of the design matrix refers to one IV.
   You will need to rely on the order of IVs in order to know which column controls which IV.
   In these cases you should use one of two alternative ways of representing IVs:
   using a :class:`collections.OrderedDict`, or a list of 2-tuples.
   Here is an example of the latter method (equivalent to the previous example):

   .. code-block:: python

      >>> independent_variables = [
      ...     ('congruent', [True, False]),
      ...     ('distractor', [None, 'left', 'right']),
      ... ]

When you specify your IVs, you will specify them separately for every level of the experiment.
That is, every IV is associated with a level of the experimental hierarchy.
This determines how often the IV value changes.
For example, a within-subjects experiment will probably have IVs at the ``'trial'`` level,
a between-subjects experiment will have IVs at the ``'participant'`` level,
and a mixed-design experiment will have both.
An IV at the ``'participant'`` level will always take the same value within each participant.
Similarly, a blocked experiment may have IVs at the ``'block'`` level;
these IVs will only take on a new value when a new block is reached.

IV values are ultimately passed to your :ref:`run callback <callbacks>` as a *condition*.
A condition is a combination of specific IV values.
Although you don't need to create conditions yourself, you can think of them as dictionaries mapping IV names to values.
For example, the six conditions generated by a full factorial cross of the IVs above are:

.. code-block:: python

   [{'congruent': True, 'distractor': None},
    {'congruent': True, 'distractor': 'left'},
    {'congruent': True, 'distractor': 'right'},
    {'congruent': False, 'distractor': None},
    {'congruent': False, 'distractor': 'left'},
    {'congruent': False, 'distractor': 'right'}]

Just like IVs, different conditions apply at different levels of the experimental hierarchy.
These conditions propagate down the tree.
For example, imagine a trial has one of the conditions in the list above,
``{'congruent': True, 'distractor': None}``.
The block that the trial is part of may have an additional condition, like ``{'practice': False}``.
When the trial is run, these conditions are effectively merged.

.. note::

   This merging is implemented with the standard-library object |collections.ChainMap|.
   A |ChainMap| can be accessed just like a dictionary;
   this is the sense in which it is correct to say that the conditions are merged.
   To continue the example, one can access the IV values without worrying about what level each IV came from:

   .. code-block:: python

      >>> condition['congruent']
      True
      >>> condition['practice']
      False

   However, it is possible to differentiate the conditions if needed,
   using the :attr:`~collections.ChainMap.maps` attribute.
   See the |ChainMap| docs for details.
   You might see something like this:

   .. code-block:: python

      >>> condition.maps[0]
      {'trial': 1,
       'congruent': True,
       'distractor': None}
      >>> condition.maps[1]
      {'block': 2,
       'practice': False}
      >>> condition.maps[2]
      {'participant': 1}

.. _orderings:

Orderings
---------

The second element of a :ref:`design <designs>` is an *ordering method*.
The ordering method determines how children of a section wll be ordered (and possibly repeated).
For example, an experiment may shuffle trials within each block,
counter-balance blocks within each session,
and put all sessions within each participant in the same order.

Each ordering method is a class in the |experimentator.order| module.
Currently, experimentator includes
|Ordering| (the base class, resulting in a deterministic order),
|Shuffle|,
|CompleteCounterbalance|,
|Sorted|, and
|LatinSquare|.
|Shuffle| is usually the default, except if you're using a |design matrix|,
in which case experimentator assumes you want a deterministic order and makes |Ordering| the default.

Each ordering method class has different parameters, so see the specific API reference for details.
Commonly, the first argument is ``number``, which specifies the number of times each condition will be repeated.
For example, with the ordering method ``Shuffle(3)``,
each unique condition will be repeated three times, and then the order will be randomized.

.. _non-atomic-orderings:

Non-atomic orderings
********************

The included ordering classes can be divided into two categories: atomic and non-atomic.
If every ordering of sections is independent of all other orderings, then the ordering method is atomic.
For example, if trials within a block are shuffled, then the ordering of trials within each block will be independent.
Each block can shuffle its trials without needing to know the order of trials within the other blocks.

However, this is not the case for non-atomic orderings.
The ordering of sections using non-atomic orderings are dependent on each other.
For example, if blocks within a session are counterbalanced using |CompleteCounterbalance|,
then each session cannot, on its own, determine the order of blocks within it.

Non-atomic orderings are implemented by automatically creating a new independent variable.
For example, if the |block| level has three conditions (e.g., one IV with three possible values)
and a |CompleteCounterbalance| ordering (with ``number=1``),
then there are six possible orderings of blocks.
A new IV called ``'counterbalance_order'`` will be automatically created one level up (e.g., at the |session| level),
with six possible values (the integers 0-5).

Don't forget to take this automatically-created IV into account when designing your experiment.
In the above example, if there are no other IVs at the |session| level, and ``number=1`` for the |session| ordering,
there will still be six sessions per participant due to the six conditions defined by the ``'counterbalance_order'`` IV.

Only |Ordering| and |Shuffle| are atomic; the other ordering methods provided in experimentator are non-atomic
(the |Sorted| ordering method straddles the line; it may or may not be atomic, depending on the parameter ``order``.
If ``order='ascending'`` or ``order='descending'``,
then the ordering method is atomic as it is sorted the same way at every section.
However, if ``order='both'``, then it is non-atomic and a new IV ``{'order': ['ascending', 'descending']}``
will be created).

.. _why levels:

Why use levels?
===============

You may be wondering how many levels to use, or why to use them at all
(after all, `flat is better than nested`_).
That decision must be made on a case-by-case basis.
For example, imagine your experiment has sessions of 20 trials, divided into two blocks.
As long as the order of conditions within each session is correctly specified
(for example, by using a |design matrix|),
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

     exp run my_exp.exp participant 1 block 2

  rather than the more awkward

  ::

     exp run my_exp.exp participant 1 --from 11

- index the data by level, after running the experiment, using :ref:`hierarchical indexing <indexing.hierarchical>`.
  For example, to get the third trial of the first participant's second block you could do

  .. code-block:: python

     experiment.dataframe.loc[(1, 2, 3), :]

  or to get the first trial of the second block of every participant,

  .. code-block:: python

     data.xs((2, 1), level=('block', 'trial'))

.. _flat is better than nested: http://legacy.python.org/dev/peps/pep-0020/

.. _heterogeneity:

Heterogeneous experiment structures
===================================

A final concept to explain is the difference between homogeneous and heterogeneous experiment structures.
In a homogeneous experiment, every section at the same level has the same :ref:`design <designs>`.
For example, if the first block contains ten trials and the second block contains twenty,
the experiment structure is heterogeneous.
If the order of blocks within the first session is random
but the order of blocks within the second session is counterbalanced,
the experiment structure is heterogeneous.
Even different possible IV values across sections is enough to break homogeneity.

Heterogeneous experiments are a little trickier to set up, but they are fully supported by experimentator.
See :ref:`constructing-heterogeneity`.
