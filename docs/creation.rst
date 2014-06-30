.. _creation:

======================
Creating an experiment
======================

The typical workflow using experimentator is relatively straightforward:

1. Create an |Experiment| instance.
2. Run the experiment using the :ref:`CLI <cli>`.
3. Inspect, analyze or export the resulting data.

There are a number of ways to create an |Experiment|.

**Simplified constructor methods.**
These methods construct |Experiment| instances based on common experimental designs.

* |Experiment.within_subjects|:
  Construct an experiment with levels |participant| and |trial|, and IVs only at the |trial| level.
  For example:

  .. code-block:: python

      from experimentator import Experiment, order

      independent_variables = {
          'side': ['left', 'right'],
          'display_time': [0.1, 0.55, 1],
      }
      experiment = Experiment.within_subjects(
          independent_variables,
          n_participants=20,
          ordering=order.Shuffle(10)
      )

  The above creates a 2 (side) by 3 (display time) within-subjects experiment,
  with 10 trials of each condition and 20 participants.
  Trials will be shuffled within participants.
* |Experiment.blocked|:
  Construct an experiment with levels |participant|, |block|, and |trial|,
  with IVs at the |trial| level (and optionally at the |block| level also).
  The following constructs an experiment identical to the previous example,
  except with each participant's 60 trials split into two blocks:

  .. code-block:: python

      from experimentator import Experiment, order

      independent_variables = {
          'side': ['left', 'right'],
          'display_time': [0.1, 0.55, 1],
      }
      experiment = Experiment.blocked(
          independent_variables,
          n_participants=20,
          orderings={
              'trial': order.Shuffle(5),
              'participant': order.Ordering(2),
          }
      )

     In the above example, it doesn't matter what ordering method we use at the |block| level;
     since there are no block-level IVs, all blocks are identical.
     We could, alternatively, introduce an IV at the block level:

  .. code-block:: python

      from experimentator import Experiment, order

      independent_variables = {
          'side': ['left', 'right'],
          'display_time': [0.1, 0.55, 1],
      }
      experiment = Experiment.blocked(
          independent_variables,
          block_ivs={'difficulty': ['easy', 'hard']}
          n_participants=20,
          orderings={'trial': order.Shuffle(5)}
      )

  In this example, we introduced the IV ``'difficulty'`` with two levels.
  Since we didn't specify an ordering for blocks, ``Shuffle(1)`` will be used.
  In other words, each participant will experience one ``'easy'`` and one ``'hard'`` block, in a random order.

.. _design-matrices:

Design matrices
===============

.. _constructing-heterogeneity:

Constructing heterogeneous experiments
======================================

.. _callbacks:

Callbacks
=========

.. _contexts:

Context-managers
----------------
