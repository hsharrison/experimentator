import os
import sys
import inspect


THINGS_TO_SHOW = [
    'self.func.__name__',
    '__name__',
    'os.path.basename(__file__)',
    'inspect.getsourcefile(self.func)',
    'inspect.getfile(inspect.currentframe())',
    'inspect.stack()[0][1]',
    'inspect.stack()[1][1]',
    'inspect.stack()[-1][1]',

]


class Dummy():
    def __init__(self):
        self.func = None

    def set_func(self, func):
        self.func = func
        return func

    def show(self):
        for thing in THINGS_TO_SHOW:
            print('{}:\n{}\n'.format(thing, eval(thing)))
