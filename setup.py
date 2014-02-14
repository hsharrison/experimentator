from setuptools import setup
from setuptools.command.test import test
import sys

with open('experimentator/__version__.py') as f:
    exec(f.read())

with open('README.rst') as f:
    readme = f.read()


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
      download_url='https://bitbucket.org/hharrison/experimentator/get/default.tar.gz',
      description='Experiment builder',
      long_description=readme,
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
      tests_require=['pytest'],
      cmdclass={'test': PyTest},
      )
