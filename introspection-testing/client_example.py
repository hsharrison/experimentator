from contextlib import contextmanager
from library_example import Dummy


desired = 'client_example'
print('\nDESIRED OUTPUT: {}\n'.format(desired))


def f():
    pass


d = Dummy()

print('-------\nPassed as argument:\n-------\n')
d.set_func(f)
arg_results = d.show()


print('-------\nDecorated function:\n-------\n')


@contextmanager
def f():
    yield

d.set_func(f)
dec_results = d.show()


for thing in arg_results.keys():
    print('{}: {}'.format(thing, 'Y' if arg_results[thing] == dec_results[thing] == desired else 'N'))
