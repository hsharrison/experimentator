# Copyright (c) 2014 Henry S. Harrison
from configparser import ConfigParser


class QuitSession(BaseException):
    """
    Raised to exit the experimental session.

    Raise this exception from inside a trial when the entire session should be exited, for example if the user presses
    a 'quit' key.

    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


def parse_config(config_file):
    """
    Parse config file(s) for experiment information.

    [Experiment]
    levels = comma-separated list
    sort methods = list, separated by commas
    number = comma-separated list of integers

    [Independent Variables]
    variable = level, comma- or semicolon-separated list of values

    That is, each entry name in the Independent Variables section is interpreted as a variable name. The entry string is
    interpreted as a comma- or semicolon-separated list. The first element should match one of the levels specified in
    the Experiment section. The other elements are the possible values (levels) of the IV. These values are interpreted
    by the Python interpreter, so proper syntax should be used for values that aren't simple strings or numbers.
    """
    if isinstance(config_file, ConfigParser):
        config = config_file
    else:
        config = ConfigParser()
        config.read_file(config_file)

    levels = config['Experiment']['levels'].split(',')
    sort_methods = config['Experiment']['sort methods'].split(',')
    number = config['Experiment']['number'].split(',')

    settings_by_level = {level: dict(sort=sort, number=int(n), ivs={})
                         for level, sort, n in zip(levels, sort_methods, number)}

    for name, entry in config['Independent Variables'].items():
        entry_split = entry.split(',')
        # Allow for ; in variable lists
        if entry_split[0] not in levels:
            entry_split = entry.split(';')

        settings_by_level[entry_split[0]]['ivs'][name] = list(eval(entry) for entry in entry_split[1:])

    return levels, settings_by_level
