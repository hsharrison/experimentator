.. meta::
    :description: Python experiment constructor
    :keywords: experimental design, experiments, Psychology

====================================================
``experimentator``: Build and run Python experiments
====================================================

``experimentator`` is a Python package for designing, constructing, and running experiments in Python. Its original purpose was for Psychology experiments, in which participants  interact with the terminal or, more commonly, a graphical interface, but there is nothing domain-specific; ``experimentator`` will be useful for any kind of experiment run with the aid of a computer. The basic use case is that you have already written code to run a single trial and would like to run a set of experimental sessions in which inputs to your trial function are systematically varied and repeated


Requirements
============

- Python 3.3 or later
- `pandas <http://pydata.pandas.org/>`_, v0.13.0 or later, required for exporting experiment data
- `docopt <http://docopt.org/>`_, v0.6.1 or later, required for using the command-line interface

Installation
============

It is recommended that you install ``experimentator`` into a `virtualenv <http://www.virtualenv.org>`_. Two utilities to make it easier to work with virtual environments are `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/>`_ (the established and more popular choice) and `pew <https://github.com/berdario/invewrapper>`_ (a relatively new option and my personal recommendation). The code in this section is to be run in the system shell in a virtual environment created with a Python 3.3 (or later) interpreter.

Using pip
---------

The latest version of ``experimentator`` can be installed using `pip <http://pip.openplans.org/>_ with the following command:

.. code-block:: sh

    pip install --upgrade experimentator

From the repositories
---------------------

The source code for ``experimentator`` is hosted on both `github <https://github.com/hsharrison/experimentator>`_ and `bitbucket <https://bitbucket.org/hharrison/experimentator>`_. The bitbucket repository is considered canonical; however they should be identical at all times. The repositories can be accessed using either `git <http://git-scm.com/>`_ (via github) or `mercurial <http://mercurial.selenic.com/>`_ (via bitbucket). If you are new to these utilities I suggest starting with either the `github <https://help.github.com/>`_ or `bitbucket <https://confluence.atlassian.com/display/BITBUCKET/Bitbucket+101>`_ help pages. I find mercurial to be easier for a beginner, however git is more popular.

Download the latest source code using one of the following commands:

.. code-block:: sh

    hg clone https://bitbucket.org/hharrison/experimentator
    # or
    git clone https://github.com/hsharrison/experimentator

Then install:

.. code-block:: sh

    cd experimentator
    python setup.py install

Bug reports and development
===========================

Use the `github issues page <https://github.com/hsharrison/experimentator/issues>`_ to report any issues or request enhancements.

You can contribute to development by forking the repository on `bitbucket <https://bitbucket.org/hharrison/experimentator/fork>`_ or `github <https://github.com/hsharrison/experimentator/fork>`_.


License
=======

This package is provided under the `MIT license <http://opensource.org/licenses/MIT>`_:

Copyright (c) 2013-2014 Henry S. Harrison

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Documentation contents
======================

.. toctree::
   :maxdepth: 2

   overview
   config_file
   an_example
   command_line
   ordering_methods
   tweaking
   api

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
