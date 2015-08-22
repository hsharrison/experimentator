from experimentator.__version__ import __version__
from experimentator.experiment import Experiment, run_experiment_section, export_experiment_data
from experimentator.design import Design, DesignTree

from collections.abc import Iterable
import yaml
import numpy as np


class QuitSession(BaseException):
    """
    An Exception indicating a 'soft' exit from a running experimental session.

    Raise this exception to indicate a desired exit;
    e.g. when the user presses a quit key.

    Parameters
    ----------
    message : str
              Message to display in the terminal.

    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


DTYPE_REPLACEMENTS = {
    'str256': '<U8',
    'str128': '<U4',
}


def add_representer(data_type):
    def actually_add(function):
        types = data_type if isinstance(data_type, Iterable) else [data_type]
        for type_ in types:
            yaml.add_representer(type_, function)
        return function
    return actually_add


def add_constructor(tag):
    def actually_add(function):
        yaml.add_constructor(tag, function)
        return function
    return actually_add


def safe_ignore_aliases(data):
    if data is None:
        return True
    if data is ():
        return True
    if isinstance(data, (str, bytes, bool, int, float)):
        return True

yaml.representer.SafeRepresenter.ignore_aliases = staticmethod(safe_ignore_aliases)


@add_representer(np.ndarray)
def ndarray_representer(dumper, data):
    return dumper.represent_list(data.tolist())


@add_representer([complex, np.complex, np.complex128])
def complex_representer(dumper, data):
    return dumper.represent_scalar('!complex', repr(data).strip('()'))


@add_constructor('!complex')
def complex_constructor(loader, node):
    return complex(node.value)


@add_representer(np.float64)
def np_float_representer(dumper, data):
    return dumper.represent_float(float(data))


@add_representer([np.int32, np.int64])
def np_int_representer(dumper, data):
    return dumper.represent_int(int(data))


@add_representer(np.dtype)
def np_dtype_representer(dumper, data):
    return dumper.represent_scalar('!dtype', data.name)


@add_constructor('!dtype')
def np_dtype_constructor(loader, node):
    name = loader.construct_scalar(node)
    return np.dtype(DTYPE_REPLACEMENTS.get(name, name))
