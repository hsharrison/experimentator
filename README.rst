=========================================
experimentator: Python experiment builder
=========================================

+--------------------+-------------------+-------------------+
| | |travis-badge|   | | |version-badge| | | |git-badge|     |
| | |coverage-badge| | | |doi-badge|     | | |license-badge| |
+--------------------+-------------------+-------------------+

.. |travis-badge| image:: http://img.shields.io/travis/hsharrison/experimentator.png?style=flat
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/hsharrison/experimentator

.. |coverage-badge| image:: http://img.shields.io/coveralls/hsharrison/experimentator.png?style=flat
    :alt: Coverage Status
    :target: https://coveralls.io/r/hsharrison/experimentator

.. |version-badge| image:: http://img.shields.io/pypi/v/experimentator.png?style=flat
    :alt: PyPi Package
    :target: https://pypi.python.org/pypi/experimentator

.. |license-badge| image:: http://img.shields.io/badge/license-MIT-blue.png?style=flat
    :alt: License
    :target: https://pypi.python.org/pypi/experimentator

.. |git-badge| image:: http://img.shields.io/badge/repo-git-lightgrey.png?style=flat
    :alt: Git Repository
    :target: https://github.com/hsharrison/experimentator
    
.. |doi-badge| image:: https://zenodo.org/badge/22554/hsharrison/experimentator.svg
    :alt: doi
    :target: https://zenodo.org/badge/latestdoi/22554/hsharrison/experimentator

`Documentation contents`_

.. _Documentation contents: http://experimentator.readthedocs.org/en/latest/#contents


Do you write code to run experiments?
If so, you've probably had the experience of sitting down to code an experiment
but getting side-tracked by all the logistics:
crossing your independent variables to form conditions,
repeating your conditions,
randomization,
storing intermediate data,
etc.
It's frustrating to put all that effort in
before even getting to what's really unique about your experiment.
Worse, it encourages bad coding practices
like copy-pasting boilerplate from someone else's experiment code
without understanding it.

The purpose of **experimentator** is
to handle all the boring logistics of running experiments
and allow you to get straight to what really interests you, whatever that may be.
This package was originally intended for behavioral experiments
in which human participants are interacting with a graphical interface,
but there is nothing domain-specific about it--it should be useful for anyone running experiments with a computer.
You might say that **experimentator** is a library for
'repeatedly calling a function while systematically varying its inputs and saving the data'
(although that doesn't do it full justice).

Not handled here
================

* graphics
* timing
* hardware interfacing
* statistics
* data processing

The philosophy of experimentator is to do one thing and do it well.
It is meant to be used with other libraries that handle the above functionality,
and gives you the freedom to choose which you prefer.
It is best suited for someone with programming experience and some knowledge of the Python ecosystem,
who would rather choose the best tool for each aspect of a project than use an all-in-one package.

Of course, there are alternatives that offer experimental design features along with other capabilities.
A selection, as well as recommended complimentary packages, are listed later in the documentation.

An example
==========

To demonstrate, let's create a simple perceptual experiment.
For the sake of example, imagine we will present some stimulus
to either the left or right side of the screen
for a specified amount of time,
and ask the participant to identify it.
We'll use a factorial 2 (side) x 3 (display time) design,
and have a total of 60 trials per participant (10 per condition).
Here's how it might look in experimentator:

.. code-block:: python

    import random
    from time import time
    from experimentator import Experiment, order


    def present_stimulus_and_get_response(stimulus, side, duration):
        # Use your imagination...
        return random.choice(['yes', 'no'])


    def run_trial(experiment, trial):
        stimulus, answer = random.choice(
            list(experiment.experiment_data['stimuli'].items()))
        start_time = time()
        response = present_stimulus_and_get_response(trial.data['side'], trial.data['display_time'])
        result = {
            'reaction_time': time() - start_time,
            'correct': response == answer
        }
        return result


    if __name__ == '__main__':
        independent_variables = {
            'side': ['left', 'right'],
            'display_time': [0.1, 0.55, 1],
        }
        stimuli_and_answers = {
            'cat.jpg': 'yes',
            'dog.jpg': 'no',
        }

        experiment = Experiment.within_subjects(independent_variables,
                                                n_participants=20,
                                                ordering=order.Shuffle(10),
                                                filename='exp_1.exp')

        experiment.experiment_data['stimuli'] = stimuli_and_answers
        experiment.add_callback('trial', run_trial)
        experiment.save()

Running this script will create the experiment in the file ``exp_1.exp``.
We can now run sessions from the command line::

    exp run exp_1.exp participant 1
    # or
    exp run exp_1.exp --next participant

Eventually, we can export the data to a text file::

    exp export exp_1.exp exp_1_data.csv

Or, access the data in a Python session:

.. code-block:: python

    from experimentator import Experiment

    data = Experiment.load('exp_1.exp').dataframe

In this example the data will be a pandas ``DataFrame`` with six columns:
two index columns with labels ``'participant'`` and ``'trial'``,
two columns from the IVs, with labels ``'side'`` and ``'display_time'``,
and two data columns with labels ``'reaction_time'`` and ``'correct'``
(the keys in the dictionary returned by ``run_Trial``).

Installation
============

.. note::

    If you use experimentator in your work, published or not,
    please `let me know <mailto:henry.schafer.harrison@gmail.com>`_.
    I'm curious to know what you use it for!
    If you do publish, citation information can be found `here <https://zenodo.org/badge/latestdoi/22554/hsharrison/experimentator>`_.

Dependencies
------------

Experimentator requires Python 3.3 or later.
It also depends on the following Python libraries:

- `numpy`_
- `pandas`_
- `docopt <http://docopt.org/>`_
- `schema <https://github.com/halst/schema>`_
- `PyYAML <http://pyyaml.org/wiki/PyYAML>`_
- `NetworkX <http://networkx.readthedocs.org/en/stable/index.html>`_

Required for tests:

- `pytest <http://pytest.org/latest/>`_

Required for generating docs:

- `Sphinx <http://sphinx-doc.org/>`_
- `numpydoc <https://github.com/numpy/numpydoc>`_
- `sphinx-rtd-theme <https://github.com/snide/sphinx_rtd_theme>`_

The easiest way to install these libraries, especially on Windows,
is with Continuum's free Python distribution `Anaconda <https://store.continuum.io/cshop/anaconda/>`_.
For experimentator, Anaconda3 or the lightweight Miniconda3 is recommended,
although you can create a Python3 ``conda`` environment regardless of which
version you initially download.

For example, to install dependencies to a clean environment (with name ``experiment``)::

    conda update conda
    conda create -n experiment python=3 pip
    source activate experiment
    conda install numpy pandas pyyaml networkx
    pip install docopt schema

From PyPi
---------

To install (and upgrade) experimentator::

    pip install --upgrade experimentator

Be sure to run ``pip`` from a Python 3 environment.

From source (development version)
---------------------------------

Experimentator is hosted on
`GitHub <https://github.com/hsharrison/experimentator>`_::

    git clone git@github.com:hsharrison/experimentator
    cd experimentator
    pip install -e . --upgrade

Other libraries
===============

*Please, feel free to submit a pull request to add your software to one of these lists.*

Alternatives
------------

The Python ecosystem offers some wonderful alternatives that provide experiment logistics
in addition to other functionality like graphics and input/output:

- `expyriment <https://code.google.com/p/expyriment/>`_:
  Graphics, input/output, hardware interfacing, data preprocessing, experimental design.
  If you are coming from the Matlab world, this is the closest thing to
  `Psychtoolbox <http://psychtoolbox.org/HomePage>`_.
- `OpenSesame <http://www.osdoc.cogsci.nl/>`_:
  An all-in-one package with a graphical interface to boot. An impressive piece of software.

Complimentary libraries
-----------------------

What about all those important things that experimentator doesn't do?
Here's a short selection.
If you're already using Python some of these will go without saying,
but they're included here for completeness:

- *experimental design*
    - `pyDOE <http://pythonhosted.org/pyDOE/>`_:
      Construct design matrices in a format that experimentator can use to build your experiment.
- *graphics*
    - `PsychoPy <http://psychopy.org/>`_:
      A stimulus-presentation library with an emphasis on calibration and temporal precision.
      Unfortunately, at the time of this writing it is not yet Python3-compatible, and so cannot be easily combined with experimentator.
    - `Pygame <http://pygame.org/news.html>`_:
      Very popular.
    - `Pyglet <http://www.pyglet.org/>`_:
      A smaller community than Pygame, but has several advantages, including cross-compatibility and a more pythonic API.
      Includes OpenGL bindings.
    - `PyOpenGL <http://pyopengl.sourceforge.net/>`_:
      If all you need is to make OpenGL calls.
- *graphical user interfaces*
    - `urwid <http://urwid.org/>`_:
      Console user interface library, ncurses-style.
    - `wxPython <http://wxpython.org/>`_:
      Python bindings for the wxWidgets C++ library.
    - `PyQT <http://www.riverbankcomputing.com/software/pyqt/intro>`_:
      QT bindings.
    - `PySide <http://qt-project.org/wiki/PySide>`_:
      Another QT option.
    - `PyGTK <http://www.pygtk.org/>`_:
      Python bindings for GTK+.
- *statistics and data processing*
    - `pandas`_:
      Convenient data structures. Experimental data in experimentator is stored in a pandas ``DataFrame``.
    - `numpy`_:
      Matrix operations. The core of the Python scientific computing stack.
    - `SciPy <http://docs.scipy.org/doc/scipy/reference/>`_:
      A comprehensive scientific computing library spanning many domains.
    - `Statsmodels <http://statsmodels.sourceforge.net/>`_:
      Statistical modeling and hypothesis testing.
    - `scikit-learn <http://scikit-learn.org/stable/>`_:
      Machine learning.
    - `rpy2 <http://rpy.sourceforge.net/rpy2.html>`_:
      Call ``R`` from Python. Because sometimes the model or test you need isn't in statsmodels or scikit-learn.

License
=======

*Licensed under the MIT license.*

.. _numpy: http://www.numpy.org
.. _pandas: http://pandas.pydata.org
