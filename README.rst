==============
experimentator
==============
-------------------------
Python experiment builder
-------------------------

Do you write code to run experiments? If so, you've probably had the experience of sitting down to code an experiment but getting side-tracked by all the logistics: crossing your independent variables to form conditions, repeating your conditions, randomization, storing intermediate data, etc. It's frustrating to put all that effort in before even getting to what's really unique about your experiment. Worse, it encourages bad coding practices like copy-pasting boilerplate from someone else's experiment code without understanding it.

The underlying purpose of **experimentator** is to handle all the boring logistics of running experiments and allow you to get straight to what really interests you, whatever that may be. This package was originally designed for behavioral experiments in which human participants are interacting with a graphical interface, but there is nothing domain-specific about it--it should be useful for anyone running experiments with a computer. You might say that **experimentator** is a library for 'repeatedly calling a function while systematically varying its inputs and saving the data', although that doesn't do full justice to its functionality.

What experimentator is not
--------------------------

The philosophy of experimentator is to do one thing and do it well. It does not do:

* graphics
* timing
* hardware interfacing
* statistics
* data processing

Experimentator is meant to be used with other libraries that handle the above functionality, and gives you the freedom to choose which you prefer. It is best suited for someone with programming experience and some knowledge of the Python ecosystem, who would rather choose the best tool for each aspect of a project than use an all-in-one package.

Of course, there are alternatives that offer experimental design features along with other capabilities. A selection, as well as recommended complimentary packages are listed at the end of this document.

An example
----------

To demonstrate, let's build a 2x3 factorial within-subjects experiment:

.. code-block:: python

    from experimentator.api import within_subjects_experiment
    from experimentator.order import Shuffle

    def present_stimulus(session_data, experiment_data, congruent=False, display_time=0.1, **context):
        # The interesting part goes here.
        # Let's imagine a stimulus is presented, and a response is collected.
        return {'reaction_time': rt, 'correct': response==answer}


    if __name__ == '__main__':
        independent_variables = {'congruent': [False, True],
                                 'display_time': [0.1, 0.55, 1]}
        distractor_experiment = within_subjects_experiment(independent_variables,
                                                           n_participants=20,
                                                           ordering=Shuffle(10),
                                                           experiment_file='distractor.dat')
        distractor_experiment.set_run_callback(present_stimulus)
        distractor_experiment.save()

This experiment has two independent variables, ``'congruent'`` with two levels, and ``'display_time'`` with three, for a total of six conditions (ignore, for now, the other elements of the function's signature). It has 20 participants, though more can be added later. The conditions are shuffled, with each appearing 10 times.

Running the above script creates ``distractor.dat``. From there, we can run sessions of the experiment straight from the command line, using the entry point ``exp``, automatically installed with experimentator:

.. code-block:: bash

    exp run distractor.dat --next participant

Finally, we can export the data to a text file:

.. code-block:: bash

    exp export distractor.dat data.csv

Or, access the data in a Python session:

.. code-block:: python

    from experimentator import load_experiment

    data = load_experiment('distractor.dat').data

In this example the data will have six columns: two index columns with labels ``'participant'`` and ``'trial'``, two columns from the IVs, with labels ``'congruent'`` and ``'display_time'``, and two data columns with labels ``'reaction_time'`` and ``'correct'`` (the keys in the dictionary returned by ``present_stimulus_data``).

Installation
------------

Dependencies
^^^^^^^^^^^^

Experimentator requires Python 3.3 or later. It also depends on the following Python libraries:

* `numpy <http://www.numpy.org/>`_ ``v1.8.0`` or later
* `pandas <http://pandas.pydata.org/>`_ ``v0.13.0`` or later
* `docopt <http://docopt.org/>`_ ``v0.6.1`` or later

Version control
^^^^^^^^^^^^^^^

Experimentator is hosted on both `GitHub <https://github.com/hsharrison/experimentator>`_ and `BitBucket <https://bitbucket.org/hharrison/experimentator>`_. The Mercurial repository (BitBucket) is considered canonical.

From PyPi
^^^^^^^^^

Assuming you are in a Python 3 virtual environment, run:

.. code-block:: bash

    pip install experimentator

to install experimentator. Use the ``--upgrade`` flag to update your copy to the newest version.

From source
^^^^^^^^^^^

From a Python 3 virtual environment:

.. code-block:: bash

    hg clone https://bitbucket.org/hharrison/experimentator
    # or
    git clone https://github.com/hsharrison/experimentator

    cd experimentator
    python setup.py install

License
-------

Licensed under the MIT License, which may or may not appear below depending on where you're reading this. If not, see ``LICENSE.txt``.

.. include:: LICENSE.txt


Other libraries
---------------

Alternatives to experimentator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Python ecosystem offers some wonderful alternatives that *do* handle experimentation logistics in addition to providing other functionality like graphics and input/output.

* `expyriment <https://code.google.com/p/expyriment/>`_: graphics, input/output, hardware interfacing, data preprocessing, experimental design. If you are coming from the Matlab world, this is the closest thing to `Psychtoolbox <http://psychtoolbox.org/HomePage>`_.
* `OpenSesame <http://www.osdoc.cogsci.nl/>`_: an all-in-one package with a graphical interface to boot. An impressive piece of software.
* Contact the `author`_ or submit a pull request and I'll add your software to this list.

Complimentary libraries
^^^^^^^^^^^^^^^^^^^^^^^

What are your options for handling the things that experimentator doesn't do? Here's a short selection. If you're already using Python some of these will go without saying, but they're included here for completeness:

* experimental design
    * `pyDOE <http://pythonhosted.org/pyDOE/>`_: Construct design matrices in a format that experimentator can use to build your experiment.
* graphics
    * `Pygame <http://pygame.org/news.html>`_: Very popular but not platform-independent.
    * `Pyglet <http://www.pyglet.org/>`_: A smaller community than Pygame, but my personal preference. Works with callbacks rather than with an explicit event loop. Platform-independent and includes OpenGL bindings.
    * `PyOpenGL <http://pyopengl.sourceforge.net/>`_: If all you need is to make OpenGL calls.
* graphical interfaces
    * `urwid <http://urwid.org/>`_: Console user interface library, ncurses-style.
    * `wxPython <http://wxpython.org/>`_: Python bindings for the wxWidgets C++ library.
    * `PyQT <http://www.riverbankcomputing.com/software/pyqt/intro>`_: QT bindings.
    * `PySide <http://qt-project.org/wiki/PySide>`_: Another QT option.
    * `PyGTK <http://www.pygtk.org/>`_: Python bindings for GTK+.
* statistics and data processing
    * `pandas <http://pandas.pydata.org/>`_ Convenient data structures. Experimental data in experimentator is stored in a pandas ``DataFrame``.
    * `NumPy <http://www.numpy.org/>`_ Matrix operations. The core of the Python scientific computing stack.
    * `SciPy <http://docs.scipy.org/doc/scipy/reference/>`_: A comprehensive scientific computing library.
    * `Statsmodels <http://statsmodels.sourceforge.net/>`_: Statistical modeling and hypothesis testing.
    * `scikit-learn <http://scikit-learn.org/stable/>`_: Machine learning in Python.
    * `rpy2 <http://rpy.sourceforge.net/rpy2.html>`_: Call ``R`` from Python. Because sometimes the model or test you need isn't in statsmodels or scikit-learn.

.. _author: mailto:henry.schafer.harrison@gmail.com
