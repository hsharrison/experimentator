.. _api_reference:

=============
API reference
=============

Experiment
==========

.. autoclass:: experimentator.Experiment
    :members:
    :show-inheritance:
    :inherited-members:

Helper functions
================

.. autofunction:: experimentator.run_experiment_section

.. autofunction:: experimentator.export_experiment_data

ExperimentSection
=================

.. autoclass:: experimentator.section.ExperimentSection
   :members:

Design
======

.. autoclass:: experimentator.Design
    :members:

DesignTree
==========

.. autoclass:: experimentator.DesignTree
    :members:


experimentator.order
====================

.. automodule:: experimentator.order
    :members: Ordering, Shuffle, NonAtomicOrdering, CompleteCounterbalance, Sorted, LatinSquare
    :show-inheritance:
