import os
import sys
import inspect


THINGS_TO_SHOW = [
    'os.path.basename(__file__)[:-3]',
    'os.path.basename(sys.argv[0])[:-3]',
    'os.path.basename(inspect.getsourcefile(self.func))[:-3]',
    'os.path.basename(inspect.stack()[1][1])[:-3]',
    'os.path.basename(inspect.stack()[-1][1])[:-3]',
    'self.func.__module__',
]


class Dummy():
    def __init__(self):
        self.func = None

    def set_func(self, func):
        self.func = func
        return func

    def show(self):
        result = {}
        for i, thing in enumerate(THINGS_TO_SHOW):
            result[thing] = eval(thing)
            print('{}. {}:\n\t{}\n'.format(i+1, thing, result[thing]))
        return result
