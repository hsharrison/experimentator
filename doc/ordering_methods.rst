.. _ orderings:

================
Ordering methods
================

Ordering methods are defined in the :mod:`experimentator.orderings` module as classes. Orderings handle the combinations of IV values to form unique conditions, the ordering of the unique conditions, and the duplication of unique conditions if specified with the ``number`` parameter. The following classes are available:

Ordering
++++++++

:class:`Ordering`. The base class. Using this will create every section in the same order. The ``number`` keyword argument duplicates the entire order (as opposed to each condition separately). For example, with two IVs taking levels of ``iv1 = ('A', 'B')`` and ``iv2 = ('a', 'b')``, ``Ordering(2)`` will probably produce the order ``('Aa', 'Ab', 'Ba', 'Bb', 'Aa', 'Ab', 'Ba', 'Bb')``. The order is non-deterministic--it is usually predictable based on the order the IVs were defined but it is not guaranteed to be stable across Python versions or implementations (if you wish to be able to specify a particular order, submit an issue or a pull request, or :ref:`manually rearrange the sections <tweaking>` after your :class:`Experiment` instance is created).

Shuffle
+++++++


:class:`Shuffle`. This ordering method randomly shuffles the sections, *after* duplicating the unique conditions according to the keyword argument ``number``. If ``avoid_repeats=True`` is passed, there will be no identical conditions back-to-back.

.. _non-atomic-orderings

Non-atomic orderings
====================

Non-atomic orderings are orderings that are not independent between sections. For example, if you want to make sure that the possible block orders are evenly distributed within participants (a counterbalanced design), that means that each participant section can't decide independently how to order the blocks--the orderings must be managed by the parent level of the experimental hierarchy (in the example of counterbalanced blocks, the :attr:`Experiment.base_section`--the experiment itself, essentially--must tell each participant what block order to use).

Non-atomic orderings work by creating a new independent variable ``order`` one level up. In the above example, when a participant section orders its blocks, it consults its IV ``order``. Note that this happens automatically, so you should not define an IV called ``order`` or it will be overwritten.

Complete counterbalance
+++++++++++++++++++++++

:class:`CompleteCounterbalance`. In a complete counterbalance, every unique ordering of the conditions appears the same numbers of times. Be warned that the number of possible orderings can get very large very quickly. Therefore, this is only recommended with a small number of conditions.

The number of unique orderings (and therefore, values of the IV ``order`` one level up) can be determined by :math:`\frac{!(n\times k)}{n**k}` where :math:`n` is the value of the keyword argument ``number`` and :math:`k` is the number of unique conditions. For example, there are 120 possible orderings of 5 conditions. With 3 conditions and ``number=2``, there are 90 unique orderings.

The values of the IV ``order`` one level up are integers, each associated with a unique order of sections.

Sorted
++++++

:class:`Sorted`. This ordering method sorts the conditions based on the value of the IV defined at its level. To avoid ambiguity, it can only be used for levels with a single IV. The keyword argument ``order`` can be any of ``('both', 'ascending', 'descending')``. For the latter two, the IV ``order`` one level up will not be created, because all sections will be sorted the same way. However, for the default ``order='both'``, an IV ``order`` is created one level up, with possible values ``'ascending'`` and ``'descending'``. That is, half the sections will be created in ascending order, and half in descending order.

Latin square
++++++++++++

:class:`LatinSquare`. This orders your sections according to a `Latin square <http://en.wikipedia.org/wiki/Latin_square>` of order equal to the number of unique conditions at the level. The values of the ``order`` IV one level up will be integers, each associated with a unique order of conditions. The number of orders will be equal to the order of the Latin square. If the keyword argument ``number > 1``, each ordering is duplicated *after* computing the Latin square. For example, with ``number=2`` and 2x2 IVs (4 total conditions), then 4 unique orderings will be generated, each consisting of a 4-condition sequence repeated twice.

If the keyword argument ``balanced==True``, then each condition will appear immediately before and after each other condition an equal number of times. Balanced Latin squares can only be constructed with an even number of conditions. If ``uniform==True`` is passed, care will be taken to sample a Latin square randomly from a uniform distribution of Latin squares. This option can only be used for unbalanced Latin squares.

Note that the algorithm for computing unbalanced Latin squares is not very efficient. On the test PC, with ``uniform=True`` and ``balanced=False`` the computation time jumps from seconds to minutes between orders 5 and 6; with ``uniform=False`` the algorithm can generate a latin square up to about an order of 10 before jumping from seconds to minutes. Higher than that, computation time will increase rapidly. With ``balanced=True``, Latin squares of arbitrarily high order can be created very quickly, because the algorithm does not randomly sample from balanced Latin squares; instead, it constructs a canonical balanced Latin square and shuffles the conditions.

.. _ordering-config

Specifying ordering methods in the config file
==============================================

In the :ref:`config file <config>`, ordering methods appear in the ``[Experiment]`` section, as a semicolon-separated list. Each item should be interpretable as a call to define an instance of an Ordering method in ``experimentator.orderings``. However, if you are not using any arguments in your call, you can leave off the parentheses. For example: ::

    [Experiment]
    levels = participant; block; trial
    orderings = Shuffle(4); CompleteCounterbalance; Shuffle(3)
