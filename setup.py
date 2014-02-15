from setuptools import setup
from setuptools.command.test import test
from distutils.version import StrictVersion
import sys
import os.path
import shutil

try:
    import numpy
except ImportError:
    raise ImportError("experimentator requires numpy, try 'pip install numpy'")

try:
    import pandas
    if StrictVersion(pandas.__version__) < StrictVersion('0.13.1'):
        raise ImportError("experimentator requires pandas >= v0.13.1, try 'pip install -U pandas'")
except ImportError:
    raise ImportError("experimentator requires pandas, try 'pip install pandas'")

#  Read version number.
with open('experimentator/__version__.py') as f:
    exec(f.read())

# Read README
with open('README.rst') as f:
    readme = f.read()

# Delete dist folder (necessary due to setuptools bug).
if os.path.exists('dist'):
    shutil.rmtree('dist')


class PyTest(test):
    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(name='experimentator',
      packages=['experimentator'],
      version=__version__,
      author='Henry S. Harrison',
      author_email='henry.schafer.harrison@gmail.com',
      url='https://bitbucket.org/hharrison/experimentator',
      license='MIT',
      download_url='https://bitbucket.org/hharrison/experimentator/get/default.tar.gz',
      description='Experiment builder',
      long_description=readme,
      keywords='experiment science psychology experimental design research',
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
      entry_points={
          'console_scripts': ['exp = experimentator.__main__:main'],
      },
      install_requires=['docopt>=0.6.1'],
      tests_require=['pytest'],
      cmdclass={'test': PyTest},
      package_data={
          '': ['*.txt', '*.rst'],
      },
      )
