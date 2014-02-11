"""Order module.

This module contains the class `Ordering` and its descendants. These classes handle how unique conditions at a
particular experimental level are ordered and duplicated. `Ordering` objects should be instantiated and passed to the
`Design` constructor; there is no reason to interact with them directly.

Of special note are non-atomic orderings: the class `NonAtomicOrdering` and its descendants. These ordering methods are
not independent between sections. For example, if you want to make sure that the possible block orders are evenly
distributed among participants (a counterbalanced design), that means that each participant section can't decide
independently how to order the blocks--the orderings must be managed by the parent level of the experimental hierarchy
(in the example of counterbalanced blocks, the `Experiment.base_section`--the experiment itself, essentially--must tell
each participant what block order to use).

"""
import itertools
import random
import logging
from math import factorial

from experimentator.common import latin_square, balanced_latin_square


class Ordering():
    """Base ordering class.

    This is the base ordering class. It will keep conditions in the order they are defined (either in the design matrix,
    or the result of a call to `itertools.product` with all the IVs at its level).

    Arguments
    ---------
    number : int, optional
        The number of times each unique condition should appear (default=1).

    """
    def __init__(self, number=1):
        self.number = number
        self.all_conditions = []

    def first_pass(self, conditions):
        """First pass of order.

        Handles operations that should only be performed once, initializing the object before ordering conditions. In
        this case, it simply duplicates the list of conditions.

        Arguments
        ---------
        conditions : sequence of dict
            A list or other sequence (often a generator) containing dictionaries, with each key being an IV name and
            each value that IV's value for that particular condition.

        Returns
        -------
        iv_name : str or tuple
            The name of the IV, for non-atomic orderings. Otherwise, an empty tuple.
        iv_values : tuple
            The possible values of the IV. Empty for atomic orderings.

        """
        self.all_conditions = self.number * list(conditions)

        return (), ()

    def get_order(self, **context):
        """Get an order of conditions.

        This is the method that is called to get an order of conditions. In this case, the conditions are always
        returned in the same default order.

        Arguments
        ---------
        **context
            Arbitrary keyword arguments describing the context of the parent section. Unused for atomic orderings.

        Returns
        -------
        list of dict
            A list of dictionaries, each specifying a condition (a combination of IVs).

        """
        return self.all_conditions

    @staticmethod
    def possible_orders(conditions, unique=True):
        """All permutations.

        Returns all possible orders of the conditions.

        Arguments
        ---------
        conditions : sequence of dict
            A list or other sequence (often a generator) containing dictionaries, with each key being an IV name and
            each value that IV's value for that particular condition.
        unique : bool, optional
            If true (the default), will only return unique orders. Otherwise, non-unique orders will occur only if two
            or more elements of `conditions` are identical. In other words, uniqueness in determining permutations is
            predicated on identity if True, and position if False.

        Yields
        ------
        list of dict
            A list of dictionaries, each representing a condition. The list defines one possible order of the
            conditions.

        """
        if unique:
            yield from set(itertools.permutations(conditions))
        else:
            yield from itertools.permutations(conditions)


class Shuffle(Ordering):
    """Randomly shuffle the conditions.

    This ordering method randomly shuffles the sections.

    Arguments
    ---------
    number : int, optional
        Number of times each condition should appear (default=1). Conditions are duplicated before shuffling.
    avoid_repeats : bool, optional
        If True (default is False), no unique conditions will appear back-to-back.

    """
    def __init__(self, avoid_repeats=False, **kwargs):
        super().__init__(**kwargs)
        self.avoid_repeats = avoid_repeats

    def get_order(self, **context):
        """Order the conditions.

        This is the method that is called to get an order of conditions. In this case, a different, random order is
        returned every time.

        Arguments
        ---------
        **context
            Arbitrary keyword arguments describing the context of the parent section. Unused for atomic orderings.

        Returns
        -------
        list of dict
            A list of dictionaries, each specifying a condition (a combination of IVs).

        """
        random.shuffle(self.all_conditions)
        if self.avoid_repeats:
            while _has_repeats(self.all_conditions):
                random.shuffle(self.all_conditions)

        return self.all_conditions


class NonAtomicOrdering(Ordering):
    """Non-atomic ordering.

    This is a base class fro non-atomic orderings, and should not be directly instantiated. Non-atomic orderings work
    by creating a new independent variable one level up. The IV name will start with an underscore, a convention to
    avoid name clashes with other IVs.

    """
    iv_name = '_order'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order_ivs = {}

    @property
    def iv(self):
        """Independent variable.

        The IV associated with this non-atomic ordering. It will be added to the design one level up in the hierarchy.

        Returns
        -------
        iv_name : str or tuple
            The name of the IV, for non-atomic orderings. Otherwise, an empty tuple.
        iv_values : seq
            The possible values of the IV. Empty for atomic orderings.
        """
        if self.order_ivs:
            return self.iv_name, list(self.order_ivs.keys())
        else:
            return (), ()

    def get_order(self, *, order, **_):
        """Order the conditions.

        This is the method that is called to get an order of conditions. For non-atomic orderings, the order will depend
        on IV values one level above.

        Arguments
        ---------
        **context
            Arbitrary keyword arguments describing the context of the parent section. For non-atomic orderings, one of
            these keyword arguments will determine the order to be used.

        Returns
        -------
        list of dict
            A list of dictionaries, each specifying a condition (a combination of IVs).

        """
        return self.order_ivs[order]


class CompleteCounterbalance(NonAtomicOrdering):
    """Complete counterbalance.

    In a complete counterbalance design, every unique ordering of the conditions appears the same numbers of times.
    Using this ordering will create an IV one level up called ``'_counterbalance_order'`` with values of integers, each
    associated with a unique ordering of the conditions at this level.

    Arguments
    ---------
    number : int, optional
        The number of times each condition should be duplicated. Note that conditions are duplicated before determining
        all possible orderings.

    Note
    ----
    The number of possible orderings can get very large very quickly. Therefore, a complete counterbalance is not
    recommended for more than 3 conditions. The number of unique orderings can be determined by
    ``factorial(number * k) // number**k``, where `k` is the number of conditions. For example, with 5 conditions there
    are 120 possible orders; with 3 conditions and ``number==2``, there are 90 unique orders.

    """
    iv_name = '_counterbalance_order'

    def first_pass(self, conditions):
        """First pass of order.

        Handles operations that should only be performed once, initializing the object before ordering conditions. In
        this case, it determines all possible orders and assigns them to values of the IV, ``'_counterbalance_order'``.

        Arguments
        ---------
        conditions : sequence of dict
            A list or other sequence (often a generator) containing dictionaries, with each key being an IV name and
            each value that IV's value for that particular condition.

        Returns
        -------
        iv_name : str
            The string ``'_counterbalance_order'``, the name of the IV created one level up.
        iv_values : list of int
            Integers, values of the IV one level up, each associated with a unique ordering of conditions.

        """
        self.all_conditions = self.number * list(conditions)

        # Warn because this might hang if this method is accidentally used with too many possible orders.
        non_distinct_orders = factorial(len(self.all_conditions))
        equivalent_orders = factorial(self.number)**len(conditions)
        logging.warning("Creating IV '_counterbalance_order' with {} levels.".format(
            non_distinct_orders//equivalent_orders))

        self.order_ivs = dict(enumerate(self.possible_orders(self.all_conditions)))
        return self.iv


class Sorted(NonAtomicOrdering):
    """Sorted conditions.

    This ordering method sorts the conditions based on the value of the IV defined at its level.

    Arguments
    ---------
    number : int, optional
        The number of times each condition should appear.
    order : {'both', 'ascending', 'descending'}, optional
        If `order` is ``'ascending'`` or ``'descending'``, all sections will be sorted the same way as this ordering
        will be atomic. No IV will be created one  level up. However, if `order` is ``'both'`` (the default), an IV
        ``'_sorted_order'`` will be created created one level up, with possible values ``'ascending'`` and
        ``'descending'``. As a result, half the sections will be created in ascending order, and half in descending
        order.

    Note
    ----
    To avoid ambiguity, `Sorted` can only be used at levels containing only one IV.

    """
    iv_name = '_sorted_order'

    def __init__(self, order='both', **kwargs):
        super().__init__(**kwargs)
        self.order = order

    def first_pass(self, conditions):
        """First pass of order.

        Handles operations that should only be performed once, initializing the object before ordering conditions. In
        this case, the conditions will be sorted based on the IV values.

        Arguments
        ---------
        conditions : sequence of dict
            A list or other sequence (often a generator) containing dictionaries, with each key being an IV name and
            each value that IV's value for that particular condition.

        Returns
        -------
        iv_name : str or tuple
            The string ``'_sorted_order`'` if `order` is ``'both'`, the name of the IV created one level up. Otherwise,
            an empty tuple to denote that no IV is to be created.
        iv_values : list of int
            Integers, values of the IV one level up, each associated with a unique ordering of conditions. If `order` is
            not ``'both'``, an empty tuple will be passed.

        """
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
            return (), ()

    def get_order(self, **context):
        """Order the conditions.

        This is the method that is called to get an order of conditions. In this case, a sorted order is returned. If
        `order` is ``'both'``, the returned order depends on the IV ``'_sorted_order'`` passed as a keyword argument.

        Arguments
        ---------
        **context
            Arbitrary keyword arguments describing the context of the parent section. In this case, only the IV
            ``'_sorted_order'`` is relevant.

        Returns
        -------
        list of dict
            A list of dictionaries, each specifying a condition (a combination of IVs).

        """
        if self.order == 'both':
            order = context['order']
        else:
            order = self.order
        return self.order_ivs[order]


class LatinSquare(NonAtomicOrdering):
    """Latin square ordering.

    This orders the conditions according to a Latin square of order equal to the number of unique conditions at the
    level (the order of the Latin square is its, apologies for the clashing terminology here). A Latin square is a 2D
    array of elements with each element appearing exactly once in each row and column. Each row is a different ordering
    of the conditions, of the same length as the number of conditions. This allows for some counterbalancing, in designs
    too large to accommodate a complete counterbalance. An IV called ``'_latin_square_row'`` will be created one level
    up. Its values are integers, and each corresponds to a row in the square.
    square

    Arguments
    ---------
    number : int, optional
        The number of times the Latin square should be repeated (default=1. Note that the duplication occurs after
        constructing the square.
    balanced : bool, optional
        If True (the default), then first-order order effects will be balanced. each condition will appear the same
        number of times immediately before and immediately after every other condition. Balanced latin squares can onl
        be constructed with an even number of conditions.
    uniform : bool, optional
        If True (default=False), the Latin square will be randomly sampled from a uniform distribution of Latin squares.
        Otherwise, the sampling will be biased. The construction of balanced, uniform Latin squares is not implemented.

    Note
    ----
    The algorithm for computing unbalanced Latin squares is not very efficient. It is not recommended to construct
    unbalanced, uniform Latin squares of order above 5; for non-uniform, unbalanced Latin squares it is safe to go up to
    an order of 10. Higher than that, computation times increase rapidly. On the flip side, the algorithm for
    constructing balanced Latin squares is fast only because it is not robust; it is very biased and only samples from
    the same limited set of balanced Latin squares. However, this is usually not an issue. For more implementation
    details, see `latin_square` and `balanced_latin_square`.

    """
    iv_name = '_latin_square_row'

    def __init__(self, balanced=True, uniform=False, **kwargs):
        if balanced and uniform:
            raise ValueError('Cannot create a balanced, uniform Latin square')
        super().__init__(**kwargs)
        self.balanced = balanced
        self.uniform = uniform

    def first_pass(self, conditions):
        """First pass of order.

        Handles operations that should only be performed once, initializing the object before ordering conditions. In
        this case, it constructs the Latin square and assigns its rows to values of the IV ``'_latin_square_row'``.

        Arguments
        ---------
        conditions : sequence of dict
            A list or other sequence (often a generator) containing dictionaries, with each key being an IV name and
            each value that IV's value for that particular condition.

        Returns
        -------
        iv_name : str
            The string ``'_latin_square_row'``, the name of the IV created one level up.
        iv_values : list of int
            Integers, values of the IV one level up, each associated with one row of the Latin square.

        """
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
