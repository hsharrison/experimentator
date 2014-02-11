.. _config:

============
Config files
============

When constructing an :class:`Experiment` instance, the structure can be generated from a configuration file, in the following format: ::

   [Experiment]
    levels = semicolon-separated list
    orderings = calls to experimentator.ordering classes, separated by semicolons

    [Independent Variables]
    variable_name = level; semicolon-separated list of values

Both entries in the ``[Experiment]`` section should have the same number of items, separated by semicolons. The ``levels`` entry names and orders the levels, and the ``orderings`` setting defines how sections at each level are ordered (see :ref:`ordering-config` for an explanation of this syntax).

Each entry name in the ``[Independent Variables]`` section (that is, the string to the left of the =) is interpreted as a variable name (and ultimately, a :ref:`keyword argument to the experiment's callbacks <callback-args>`. The entry value (to the right of the =) is interpreted as a semicolon-separated list. The first element should match one of the levels specified in the ``[Experiment]`` section. This is the level to associate this variable with--the level it varies over. The other elements are the possible values of the IV. These strings are evaluated by the Python interpreter, so proper syntax should be used for values that aren't simple numbers (this allows your IVs to take on values of dictionaries or lists, for example). This means, for example, that values that are strings should be enclosed in quotes.

Other sections of the config file are saved as dictionaries, passed to callbacks as the ``persistent_data`` :ref:`argument <callback-args>`. Fonts and colors are parsed according to the formats below (purely for your convenience to use them in your experiment--``experimentator`` does not use fonts or colors in any way), and are identified by either appearing in their own sections ``[Fonts]`` and ``[Colors]`` or on their own line with the label ``font`` or ``color``. Everything else will be parsed as strings, so it is up to you to change types of elements of ``experiment_data`` after your :class:`Experiment` instance is created.

Colors are three integers separated by commas, and fonts are a string and then an integer. For example: ::

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

This example will generate the following ``experiment_data``:

.. code-block::

    {'colors': {'white': (255, 255, 255), 'black': 0, 0, 0},
     'fonts': {'title': ('Times', 48), 'text': ('Monaco', 12)},
     'score': {'color': (255, 0, 255), 'font': ('Garamond', 24), 'points_to_win': '100'},
    }

Note that all section names are transformed to lowercase.
