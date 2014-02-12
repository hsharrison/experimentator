from distutils.core import setup

with open('experimentator/__version__.py') as f:
    exec(f.read())

with open('README.rst') as f:
    readme = f.read()

setup(name='experimentator',
      packages=['experimentator'],
      py_modules=['experimentator', 'experimentator.orderings', 'experimentator.api'],
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
      )
