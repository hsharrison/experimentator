# Copyright (c) 2014 Henry S. Harrison

import itertools
import random
import logging
from math import factorial


class Ordering():
    def __init__(self, repeats=1, **_):
        self.repeats = repeats
        self.all_conditions = []

    def first_pass(self, ivs):
        self.all_conditions = self.repeats * list(self.conditions(ivs))
        return {}

    def order(self, **_):
        return self.all_conditions

    @staticmethod
    def conditions(ivs):
        try:
            iv_names, iv_values = zip(*ivs.items())
        except ValueError:
            # Workaround because zip doesn't want to return two elements if ivs is empty.
            iv_names = ()
            iv_values = ()
        iv_combinations = itertools.product(*iv_values)

        yield from (dict(zip(iv_names, iv_combination)) for iv_combination in iv_combinations)

    @staticmethod
    def possible_orders(combinations):
        yield from set(itertools.permutations(combinations))


class Shuffle(Ordering):
    def order(self, **_):
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
    def first_pass(self, ivs):
        conditions = list(self.conditions(ivs))
        self.all_conditions = self.repeats * conditions

        # Warn because this might hang if this method is accidentally used with too many possible orders.
        non_distinct_orders = factorial(len(self.all_conditions))
        equivalent_orders = factorial(self.repeats)**len(conditions)
        logging.warning("Creating IV 'order' with {} levels.".format(non_distinct_orders//equivalent_orders))

        self.order_ivs = dict(enumerate(self.possible_orders(self.all_conditions)))
        return self.iv


class Sorted(NonAtomicOrdering):
    def __init__(self, order='both', **kwargs):
        super().__init__(**kwargs)
        self.order = order

    def first_pass(self, ivs):
        if len(ivs) > 1:
            raise ValueError("Ordering method 'Sorted' only works with one IV.")

        self.all_conditions = self.repeats * list(self.conditions(ivs))
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
