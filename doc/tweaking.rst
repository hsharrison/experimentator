.. _tweaking:

========================
Tweaking your experiment
========================

Until the API becomes more flexible, it's useful to know how to manually tweak an :class:`Experiment` instance. This can be done via methods on the instance itself, methods of :class:`ExperimentSection` instances it contains, and helper functions imported with ``experimentator``.

The first step, usually, is to load the experiment from disk, using the :func:`load_experiment` helper function.

.. code-block::

    from experimentator import load_experiment
    exp = load_experiment('my_experiment.dat')

Adding sections
===============

As an example, you may be unhappy about having to define the number of participants in advance. What if you want to run more participants later? Use the :meth:`Experiment.add_section` method. It works like this:

.. code-block::

    exp.add_section()
    exp.save()

This would add a section to the experiment at the highest level (usually, a participant). To add lower sections, pass keyword arguments to specify the parent section. For example, ``exp.add_section(participant=1)`` will add a session (or whatever is the next level of the hierarchy) under the first participant.

Any other keyword arguments to :meth:`Experiment.add_section` define IV values, for example ``exp.add_section(participant=1, dual_task=True)`` to add a particular sort of session. Any IV values (at the level of the section you're adding) that aren't passed will be chosen randomly from the values they are configured to take.

Rearranging sections
====================

You can also use the :attr:`ExperimentSection.children` attribute to inspect and rearrange sections. Use the :meth:`Experiment.section` method to find the :class:`ExperimentSection` instance you're looking for, and then the :attr:`ExperimentSection.children` attribute is a list of :class:`ExperimentSection` instances one level down (Note that section numbers are indexed by 0 in the :attr:`ExperimentSection.children` list, although elsewhere in ``experimentator`` 1-based indexing is used). Also, you can get to the base section (the root of the experiment's hierarchy) via the :attr:`Experiment.base_section` attribute, and from there descend the hierarchy.

This example code creates a 'practice' block for each participant, with only 5 trials, as the first block in each session, using the :attr:`ExperimentSection.children` attribute and the :meth:`Experiment.section` and :method:`Experiment.add_section` methods.:

.. code-block::

    from experimentator import load_experiment
    exp = load_experiment('my_experiment.dat')

    for n in range(1,11):

        # Add a block to each session.
        for s in range(1,3):
            exp.add_section(participant=n, session=s)

            # Move the last block of the session to the beginning.
            session = exp.section(participant=n, session=s)
            blocks = session.children
            session.children = [blocks[-1], block[:-1]]

            # Remove all but the first 5 trials.
            exp.section(participant=n, session=s, block=1).children[5:] = []

    exp.save()

Eventually, I hope to make this unnecessary by improving the experiment creation API. If you have any suggestions as to the API you would prefer for this sort of thing, let me know.
