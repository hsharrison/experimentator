"""experimentator

Usage:
  exp run [options] <exp-file> (--next <level>  [--not-finished] | (<level> <n>)...)
  exp resume [options] <exp-file> <level> [<n> (<level> <n>)...]
  exp export <exp-file> <data-file> [ --no-index-label --delim <sep> --skip <columns> --float <format> --nan <rep>]
  exp -h | --help
  exp --version

Run/resume options:
  -h, --help        Show full help.
  --version         Print the installed version number of experimentator.
  -d --debug        Set logging level to DEBUG.
  -o <options>      Pass <options> to the experiment and save it as string in Experiment.session_data['options'].
  --demo            Don't save data.
  --not-finished    Run the first <level> that hasn't finished (rather than first that hasn't started).
  --skip-parents    Don't enter context of parent levels.

Export options (see pandas.Dataframe.to_csv documentation) :
  --no-index-label    Don't put column labels on index columns (e.g. participant, trial), for easier importing into R.
  --delim <sep>       Field delimiter [default: ,].
  --skip <columns>    Comma-separated list of columns to skip.
  --float <format>    Format string for floating point numbers.
  --nan <rep>         Missing data representation.

Commands:
  run <exp-file> --next <level>        Runs the first <level> that hasn't started. E.g.:
                                         exp run exp1.dat --next session

  run <exp-file> (<level> <n>)...      Runs the section specified by any number of <level> <n> pairs. E.g.:
                                         exp run exp1.dat participant 3 session 1

  resume <exp-file> <level>            Resume the first section at <level> that has been started but not finished.

  resume <exp-file> (<level> <n>)...   Resume the section specified by any number of <level> <n> pairs. The specified
                                       section must have been started but not finished. E.g.:
                                         exp resume exp1.dat participant 2 session 2

  export <exp-file> <data-file>      Export the data in <exp-file> to csv format as <data-file>.
                                     Note: This will not produce readable csv files for experiments with results as
                                           collections (e.g., series, dict). Either write a custom export script, or
                                           skip the problematic column(s) using the --skip <columns> option.

"""
import sys
import os
import logging
from docopt import docopt
from schema import Schema, Use, And, Or, Optional

from experimentator import __version__, Experiment, run_experiment_section, export_experiment_data


def main(args=None):
    # The console script created by setuptools takes the cwd off the path.
    sys.path.insert(0, os.getcwd())

    scheme = Schema({Optional('--debug'): bool,
                     Optional('--delim'): str,
                     Optional('--demo'): bool,
                     Optional('--help'): bool,
                     Optional('--float'): Or(None, str),
                     Optional('--next'): bool,
                     Optional('--nan'): Or(None, str),
                     Optional('--no-index-label'): bool,
                     Optional('--not-finished'): bool,
                     Optional('-o'): Or(None, str),
                     Optional('--skip'): Or(None, Use(lambda x: x.split(','))),
                     Optional('--skip-parents'): bool,
                     Optional('--version'): bool,
                     Optional('<data-file>'): Or(None, str),
                     Optional('<exp-file>'): Or(lambda x: x is None, os.path.exists, error='Invalid <exp-file>'),
                     Optional('<level>'): [str],
                     Optional('<n>'): [And(Use(int), lambda n: n > 0)],
                     Optional('export'): bool,
                     Optional('resume'): bool,
                     Optional('run'): bool,
                     })

    options = scheme.validate(docopt(__doc__, argv=args, version=__version__))

    if options['--debug']:
        logging.basicConfig(level=logging.DEBUG)

    if options['run'] or options['resume']:
        exp = Experiment.load(options['<exp-file>'])
        kwargs = {'demo': options['--demo'],
                  'parent_callbacks': not options['--skip-parents'],
                  'resume': options['resume'],
                  'session_options': options['-o'],
                  }

        if options['--next']:
            kwargs.update(section_obj=exp.find_first_not_run(
                options['<level>'][0], by_started=not options['--not-finished']))

        elif options['resume'] and not options['<n>']:
            kwargs.update(section_obj=exp.find_first_partially_run(options['<level>'][0]))

        else:
            kwargs.update(zip(options['<level>'], options['<n>']))

        run_experiment_section(exp, **kwargs)

    elif options['export']:
        export_experiment_data(options['<exp-file>'], options['<data-file>'],
                               float_format=options['--float'],
                               skip_columns=options['--skip'],
                               index_label=False if options['--no-index-label'] else None,
                               na_rep=options['--nan'],
                               sep=options['--delim'])
