# Copyright (c) 2013-2014 Henry S. Harrison

from distutils.core import setup

with open('experimentator/__version__.py') as f:
    exec(f.read())

setup(name='experimentator',
      packages=['experimentator'],
      py_modules=['experimentator', 'experimentator.section', 'experimentator.orderings'],
      version=__version__,
      author='Henry S. Harrison',
      author_email='henry.schafer.harrison@gmail.com',
      url='https://bitbucket.org/hharrison/experimentator',
      download_url='https://bitbucket.org/hharrison/experimentator/get/default.tar.gz',
      description='Experiment builder',
      long_description="""\
Experiment builder
------------------

experimentator is a Python package for designing, constructing, and running experiments in Python. Its original purpose was for Psychology experiments, in which participants  interact with the terminal or, more commonly, a graphical interface, but there is nothing domain-specific; experimentator will be useful for any kind of experiment run with the aid of a computer. The basic use case is that you have already written code to run a single trial and would like to run a set of experimental sessions in which inputs to your trial function are systematically varied and repeated.


Currently, experimentator requires Python 3.3 or later.
      """,
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Science/Research',
          'Topic :: Scientific/Engineering',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Utilities',
      ],
    )
