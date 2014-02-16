"""Usage:
  exp run <experiment-file> (--next <level>  [--not-finished] | (<level> <n>)...) [--demo] [--debug] [--skip-parents]
  exp  export <experiment-file> <data-file> [--debug]
  exp -h | --help
  exp --version


Commands:
  run <experiment-file> --next <level>      Runs the first <level> that hasn't started. E.g.:
                                              exp run experiment1.dat --next session

  run <experiment-file> (<level> <n>)...    Runs the section specified by any number of level=n pairs. E.g.:
                                              exp run experiment1.dat participant 3 session 1

  export <experiment-file> <data-file>      Export the data in <experiment_file> to csv format as <data_file>.
                                              Note: This will not produce readable csv files for experiments with
                                                    results in multi-element data structures (e.g., timeseries, dicts).

Options:
  --not-finished     Run the next <level> that hasn't finished (rather than first that hasn't started).
  --demo             Don't save data.
  --debug            Set logging level to DEBUG.
  --skip-parents     Don't call start and end callbacks of parent levels.
  -h, --help         Show this screen.
  --version          Print the installed version number of experimentator.

"""


def main():
    import logging
    import sys
    from docopt import docopt

    from experimentator import load_experiment, run_experiment_section, export_experiment_data, __version__

    options = docopt(__doc__, version=__version__)

    if options['--debug']:
        logging.basicConfig(level=logging.DEBUG)

    if options['run']:
        cli_exp = load_experiment(options['<experiment-file>'])
        cli_demo = options['--demo']
        parent_callbacks = not options['--skip-parents']
        if options['--next']:
            cli_section = cli_exp.find_first_not_run(options['<level>'][0], by_started=options['--not-finished'])
            run_experiment_section(cli_exp, demo=cli_demo, parent_callbacks=parent_callbacks, section=cli_section)
        else:
            run_experiment_section(cli_exp, demo=cli_demo, parent_callbacks=parent_callbacks,
                                   **dict(zip(options['<level>'], options['<n>'])))

    elif options['export']:
        export_experiment_data(options['<experiment-file>'], options['<data-file>'])

    sys.exit(0)

if __name__ == '__main__':
    main()
