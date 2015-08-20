from setuptools import setup, find_packages
from os.path import join, splitext, basename, dirname
from glob import glob

#  Read version number.
exec(open('src/experimentator/__version__.py').read())


def read(*names, **kwargs):
    return open(join(dirname(__file__), *names), encoding=kwargs.get('encoding', 'utf8')).read()


setup(name='experimentator',
      version=__version__,
      license='MIT',

      description='Experiment builder',
      long_description=read('README.rst'),

      author='Henry S. Harrison',
      author_email='henry.schafer.harrison@gmail.com',

      url='http://experimentator.readthedocs.org',
      download_url='https://bitbucket.org/hharrison/experimentator/get/default.tar.gz',

      packages=find_packages('src'),
      package_dir={'': 'src'},
      py_modules=[splitext(basename(file))[0] for file in glob('src/*.py')],
      zip_safe=True,

      keywords='experiment science psychology experimental design research',
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
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

      install_requires=[
          'numpy',
          'pandas',
          'docopt',
          'schema',
          'pyyaml',
          'networkx',
      ],
      )
