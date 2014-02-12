==============
experimentator
==============
-------------------------
Python experiment builder
-------------------------

Do you write code to run experiments? If so, you've probably had the experience of sitting down to code an experiment but getting side-tracked by all the logistics: crossing your independent variables to form conditions, repeating your conditions, randomization, storing intermediate data, etc. It's frustrating to put all that effort in before even getting to what's really unique about your experiment. Worse, it encourages bad coding practices like copy-pasting boilerplate from someone else's experiment code without understanding it.

The underlying purpose of **experimentator** is to handle all the boring logistics of running experiments and allow you to get straight to what really interests you, whatever that may be. This package was originally designed for behavioral experiments in which human participants are interacting with a graphical interface, but there is nothing domain-specific about it--it should be useful for anyone running experiments with a computer. You might say that **experimentator** is a library for 'repeatedly calling a function while systematically varying its inputs and saving the data'. Although that doesn't do full justice to its functionality.

What experimentator is not
--------------------------

The philosophy of experimentator is to do one thing and do it well. It does not do:

* graphics
* timing
* hardware interfacing
* statistics
* data processing

Experimentator is meant to be used with other libraries that handle the above functionality, and gives you the freedom to choose which you prefer. It is best suited for someone with programming experience and some knowledge of the Python ecosystem. After all, building a graphics library is hard. It's probably best to stick with one that's widely used by a variety of developers (i.e., not just experimentalists).

Of course, there are alternatives that offer experimental design features along with other capabilities. A selection, as well as recommended complimentary packages are listed at the end of this document.

An example
----------

To demonstrate, let's build a 2x3 factorial within-subjects experiment::

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

If the previous code was saved in a file called ``distractor.py``, then running it from the command line creates ``distractor.dat`` (the filenames are arbitrary--though giving them similar names is a convention)::

    python distractor.py

From there, we can run sessions of the experiment straight from the command line::

    python -m experimentator run distractor.dat --next participant

Finally, we can export the data to a text file::

    python -m experimentator export distractor.dat data.csv

Or, access the data in a Python session::

    from experimentator import load_experiment

    data = load_experiment('distractor.dat').data

Installation
------------

Dependencies
^^^^^^^^^^^^

Experimentator requires Python 3.3 or later. It also depends on the following Python libraries:

* `numpy <http://www.numpy.org/>`_ v1.8.0 or later
* `pandas <http://pandas.pydata.org/>`_ v0.13.0 or later
* `docopt <http://docopt.org/>`_ v0.6.1 or later

Version control
^^^^^^^^^^^^^^^

Experimentator is hosted on both `GitHub <https://github.com/hsharrison/experimentator>`_ and `BitBucket <https://bitbucket.org/hharrison/experimentator>`_, thanks to the `hg-git <http://hg-git.github.io/>`_ extension. The Mercurial repository is considered canonical.

From PyPi
^^^^^^^^^

Assuming you are in a Python3 virtual environment, run ::

    pip install experimentator

to install experimentator. Use the ``--upgrade`` flag to update your copy to the newest version.

From source
^^^^^^^^^^^

From a Python3 virtual environment::

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

With that in mind, the Python ecosystem offers some wonderful alternatives that *do* do some of the things on the above list:

* `expyriment <https://code.google.com/p/expyriment/>`_: graphics, input/output, hardware interfacing, data preprocessing, some experimental design features. For an all-in-one package, this is your best bet. If you are coming from the Matlab world, this is the closest thing to `Psychtoolbox <http://psychtoolbox.org/HomePage>`_.
* `OpenSesame <http://www.osdoc.cogsci.nl/>`_: an all-in-one package with a graphical interface to boot. An impressive piece of software.
* Contact the `author`_ or submit a pull request and I'll add your software to this list.

Complimentary libraries
^^^^^^^^^^^^^^^^^^^^^^^

What are your options for handling the things that **experimentator** doesn't do? Here's a short selection:

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

.. _author: mailto:henry.schafer.harrison@gmail.com
