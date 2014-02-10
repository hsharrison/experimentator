import itertools
import random
import logging
from math import factorial

from experimentator.common import latin_square, balanced_latin_square


class Ordering():
    def __init__(self, number=1, **_):
        self.number = number
        self.all_conditions = []

    def first_pass(self, conditions):
        self.all_conditions = self.number * list(conditions)
        return {}

    def order(self, **_):
        return self.all_conditions

    @staticmethod
    def possible_orders(combinations):
        yield from set(itertools.permutations(combinations))


class Shuffle(Ordering):
    def __init__(self, number=1, avoid_repeats=False, **kwargs):
        super().__init__(number=number, **kwargs)
        self.avoid_repeats = avoid_repeats

    def order(self, **_):
        random.shuffle(self.all_conditions)
        if self.avoid_repeats:
            while _has_repeats(self.all_conditions):
                random.shuffle(self.all_conditions)

        return self.all_conditions


class NonAtomicOrdering(Ordering):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order_ivs = {}

    @property
    def iv(self):
        return {'order': list(self.order_ivs.keys())}

    def order(self, *, order, **_):
        return self.order_ivs[order]


class CompleteCounterbalance(NonAtomicOrdering):
    def first_pass(self, conditions):
        self.all_conditions = self.number * list(conditions)

        # Warn because this might hang if this method is accidentally used with too many possible orders.
        non_distinct_orders = factorial(len(self.all_conditions))
        equivalent_orders = factorial(self.number)**len(conditions)
        logging.warning("Creating IV 'order' with {} levels.".format(non_distinct_orders//equivalent_orders))

        self.order_ivs = dict(enumerate(self.possible_orders(self.all_conditions)))
        return self.iv


class Sorted(NonAtomicOrdering):
    def __init__(self, number=1, order='both', **kwargs):
        super().__init__(number=number, **kwargs)
        self.order = order

    def first_pass(self, conditions):
        if len(conditions[0]) > 1:
            raise ValueError("Ordering method 'Sorted' only works with one IV.")

        self.all_conditions = self.number * list(conditions)
        self.order_ivs = {'ascending': sorted(self.all_conditions,
                                              key=lambda condition: list(condition.values())[0]),
                          'descending': sorted(self.all_conditions,
                                               key=lambda condition: list(condition.values())[0],
                                               reverse=True)}

        if self.order == 'both':
            logging.warning("Creating IV 'order' with levels 'ascending' and 'descending'.")
            return self.iv
        else:
            return {}

    def order(self, **kwargs):
        if self.order == 'both':
            order = kwargs['order']
        else:
            order = self.order
        return self.order_ivs[order]


class LatinSquare(NonAtomicOrdering):
    def __init__(self, number=1, balanced=True, uniform=False, **kwargs):
        if balanced and uniform:
            raise ValueError('Cannot create a balanced, uniform Latin square')
        super().__init__(number=number, **kwargs)
        self.balanced = balanced
        self.uniform = uniform

    def first_pass(self, conditions):
        self.all_conditions = list(conditions)
        order = len(self.all_conditions)

        if self.balanced:
            square = balanced_latin_square(order)

        else:
            if self.uniform:
                uniform_string = ''
            else:
                uniform_string = 'non-'
            logging.warning('Constructing Latin square of order {} from a {}uniform distribution...'.format(
                order, uniform_string))

            square = latin_square(order, uniform=self.uniform, reduced=not self.uniform, shuffle=not self.uniform)
            logging.warning('Latin square construction complete.')

        self.order_ivs = [self.number * [self.all_conditions[i] for i in row] for row in square]

        logging.warning("Creating IV 'order' with {} levels.".format(order))
        return self.iv


def _has_repeats(seq):
    return any(first == second for first, second in zip(seq[:-1], seq[1:]))
