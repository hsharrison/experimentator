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

    Other sections of the config file are saved as dicts in the config_data output. Fonts and colors are parsed
    according to the formats below, and are identified as either appearing in their own sections 'Fonts' and 'Colors'
    are on their own line with the label 'font' or 'color'.

    Colors are three integers separated by commas, and fonts are a string and then an integer. For example:

    [Colors]
    white = 255, 255, 255
    black = 0, 0, 0

    [Fonts]
    title = Times, 48
    text = Monaco, 12

    [Score]
    color = 255, 0, 255
    font = Garamond, 24

    Note that all section names are transformed to lowercase.

    """
    if isinstance(config_file, ConfigParser):
        config = config_file
    else:
        config = ConfigParser()
        config.read_file(config_file)

    # Parse [Experiment].
    levels = config.get('Experiment', 'levels').split(',')
    sort_methods = config.get('Experiment', 'sort methods').split(',')
    number = config.get('Experiment', 'number').split(',')

    # Parse [Independent Variables].
    settings_by_level = {level: dict(sort=sort, number=int(n), ivs={})
                         for level, sort, n in zip(levels, sort_methods, number)}

    for name, entry in config['Independent Variables'].items():
        entry_split = entry.split(',')
        # Allow for ; in variable lists
        if entry_split[0] not in levels:
            entry_split = entry.split(';')

        settings_by_level[entry_split[0]]['ivs'][name] = list(eval(entry) for entry in entry_split[1:])

    # Parse remaining sections.
    config_data = {}
    for section_label, section in config.items():
        if section_label == 'Fonts':
            config_data['fonts'] = {
                item_label: parse_font(item_string) for item_label, item_string in section.items()}
        elif section_label == 'Colors':
            config_data['colors'] = {
                item_label: parse_color(item_string) for item_label, item_string in section.items()}
        elif section_label not in ('DEFAULT', 'Experiment', 'Independent Variables'):
            config_data[section_label.lower()] = dict(section)
            if 'font' in config_data[section_label]:
                config_data[section_label]['font'] = parse_font(config_data[section_label]['font'])
            if 'color' in config_data[section_label]:
                config_data[section_label]['color'] = parse_font(config_data[section_label]['color'])

    return levels, settings_by_level, config_data


def parse_font(config_string):
    split_string = config_string(',')
    if len(split_string) != 2:
        raise ValueError('Cannot parse font config string {}.'.format(config_string))
    return dict(name=split_string[0], size=int(split_string[1]))


def parse_color(config_string):
    split_string = config_string.split(',')
    if len(split_string) != 3:
        raise ValueError('Cannot parse color string {}'.format(config_string))
    return tuple(int(i) for i in split_string)
