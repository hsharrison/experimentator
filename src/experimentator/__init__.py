from experimentator._patched_yaml import yaml
from experimentator.__version__ import __version__
from experimentator.experiment import Experiment, run_experiment_section, export_experiment_data
from experimentator.design import Design, DesignTree


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
