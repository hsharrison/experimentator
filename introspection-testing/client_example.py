from library_example import Dummy

print('\nDESIRED OUTPUT: client_example\n')


def f():
    pass


d = Dummy()

print('-------\nPassed as argument:\n-------\n')
d.set_func(f)
d.show()

print('-------\nPassed in decorator:\n-------\n')


@d.set_func
def f():
    pass


d.show()
