# Copyright (c) 2014 Henry S. Harrison
from configparser import ConfigParser

import experimentator.orderings


def parse_config(config_file):
    """
    Parse config file(s) for experiment information.

    [Experiment]
    levels = semicolon-separated list
    orderings = names of ordering methods, separated by semicolons

    [Independent Variables]
    variable name = level; semicolon-separated list of values

    In the `Experiment` section, all three lines should have the same number of items, separated by commas. The `levels`
    setting names the levels, and the `orderings` setting defines how they are ordered (and possibly repeated; more on
    ordering methods below).

    Each setting in the `Independent Variables` section (that is, the name on the right of the `=`) is interpreted as a
    variable name. The entry string (to the left of the `=` is interpreted as a comma- or semicolon-separated list. The
    first element should match one of the levels specified in the Experiment section. This is the level to associate
    this variable with. The other elements are the possible values of the IV. These values are interpreted by the Python
    interpreter, so proper syntax should be used for values that aren't simple numbers (this allows your IVs to take on
    values of dicts or lists, for example). This means that values that are strings should be enclosed in quotes.

    Other sections of the config file are saved as dicts in the experiment's `persistent_data` attribute. Fonts and
    colors are parsed according to the formats below, and are identified as either appearing in their own sections
    'Fonts' and 'Colors' are on their own line with the label 'font' or 'color'. Everything else will be parsed as
    strings, so it is up to you to change types on elements of `persistent_data` after your experiment instance is
    created.

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
    points_to_win = 100

    This example will produce the following `persistent data`:

    {'colors': {'white': (255, 255, 255), 'black': 0, 0, 0},
     'fonts': {'title': ('Times', 48), 'text': ('Monaco', 12)},
     'score': {'color': (255, 0, 255), 'font': ('Garamond', 24), 'points_to_win': '100'},
    }

    Note that all section names are transformed to lowercase.

    """
    if isinstance(config_file, ConfigParser):
        config = config_file
    else:
        config = ConfigParser()
        config.read(config_file)

    # Parse [Experiment].
    levels = list(map(str.strip, config.get('Experiment', 'levels').split(';')))
    orderings = (parse_ordering(str.strip(s)) for s in config.get('Experiment', 'orderings').split(';'))

    # Parse [Independent Variables].
    settings_by_level = {level: dict(sort=sort, ivs={})
                         for level, sort in zip(levels, orderings)}

    for name, entry in config['Independent Variables'].items():
        entry_split = list(map(str.strip, entry.split(';')))
        settings_by_level[entry_split[0]]['ivs'][name] = list(map(eval, entry_split[1:]))

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
            config_data_section = config_data[section_label.lower()]
            if 'font' in config_data_section:
                config_data_section['font'] = parse_font(config_data_section['font'])
            if 'color' in config_data_section:
                config_data_section['color'] = parse_color(config_data_section['color'])

    return levels, settings_by_level, config_data


def parse_font(config_string):
    split_string = config_string.split(',')
    if len(split_string) != 2:
        raise ValueError('Cannot parse font config string {}.'.format(config_string))
    return dict(name=split_string[0], size=int(split_string[1]))


def parse_color(config_string):
    split_string = config_string.split(',')
    if len(split_string) != 3:
        raise ValueError('Cannot parse color string {}'.format(config_string))
    return tuple(map(int, split_string))


def parse_ordering(ordering_string):
    # TODO: Allow for custom orderings by external reference.
    if '(' not in ordering_string:
        ordering_string.append('()')
    return exec('experimentator.orderings.' + ordering_string)
