"""
Usage:
  experimentator run <experiment_file> (--next <level>  [--not-finished] | (<level> <n>)...) [--demo] [--debug]
  experimentator  export <experiment_file> <data_file> [--debug]
  experimentator -h | --help
  experimentator --version


Commands:
  run <experiment_file> --next <level>      Runs the first <level> that hasn't started. E.g.:
                                              experimentator.py run experiment1.dat --next session

  run <experiment_file> (<level> <n>)...    Runs the section specified by any number of level=n pairs. E.g.:
                                              experimentator.py run experiment1.dat participant 3 session 1

  export <experiment_file> <data_file>      Export the data in <experiment_file> to csv format as <data_file>.
                                              Note: This will not produce readable csv files for experiments with
                                                    results in multi-element data structures (e.g., timeseries, dicts).

Options:
  --not-finished     Run the next <level> that hasn't finished.
  --demo             Don't save data.
  --debug            Set logging level to DEBUG.
  -h, --help         Show this screen.
  --version          Print the installed version number of experimentator.
"""

import logging
from docopt import docopt

from experimentator import load_experiment, run_experiment_section, export_experiment_data, __version__

options = docopt(__doc__, version=__version__)

if options['--debug']:
    logging.basicConfig(level=logging.DEBUG)

if options['run']:
    cli_exp = load_experiment(options['<experiment_file>'])
    cli_demo = options['--demo']
    if options['--next']:
        cli_section = cli_exp.find_first_not_run(options['<level>'][0], by_started=options['--not-finished'])
        run_experiment_section(cli_exp, demo=cli_demo, section=cli_section)
    else:
        run_experiment_section(cli_exp, demo=cli_demo, **dict(zip(options['<level>'], options['<n>'])))

elif options['export']:
    export_experiment_data(options['<experiment_file>'], options['<data_file>'])
