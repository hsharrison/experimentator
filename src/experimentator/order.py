"""
This module contains the class |Ordering| and its descendants.
These classes handle how unique conditions at a particular experimental level are ordered and duplicated.
|Ordering| instances should be passed directly to the |Design| constructor;
there is no reason to otherwise interact with them in normal use.

Of special note are non-atomic orderings:
the class |NonAtomicOrdering| and its descendants.
''Non-atomic'' here means that the orderings between sections are not independent.
A |Shuffle| ordering is atomic;
the order in one section is independent of the order in another.
However, if one wants to ensure, for example, that possible block orders are evenly distributed among participants
(a |counterbalanced design|),
the block orders within each participants are not independent.
Each participant can decide its order of blocks only in the context of the other participants' block orders.
This means that the *parent* section must handle orderings
(in the example of counterbalanced blocks,
the |Experiment.base_section|--the experiment itself, essentially--must tell each participant what block order to use).

"""
import itertools
import random
import logging
from collections import deque, namedtuple
from math import factorial
from experimentator._util import ClassSchema

logger = logging.getLogger(__name__)

IndependentVariable = namedtuple('IndependentVariable', ('name', 'values'))


class Ordering:
    """
    The base ordering class.
    It will keep conditions in the order they are defined by the |Design| instance
    (either the order of rows in the design matrix,
    or a full factorial cross--the output of calling |itertools.product| on the IV levels).
    Remember not to rely on the order of dictionary items.
    Therefore, if a specific order is desired,
    it is recommended to use a design matrix or an |OrderedDict| to define the IVs.
    See the |IV docs| for more information.

    Parameters
    ----------
    number : int, optional
        The number of times each unique condition should appear.
        The default is 1.
        If ``number > 1``, the entire order will be cycled
        (as opposed to repeating each condition within the order).

    """
    def __init__(self, number=1):
        self.number = number
        self.all_conditions = []

    def __repr__(self):
        return '{}(number={})'.format(self.__class__.__name__, self.number)

    def first_pass(self, conditions):
        """
        Handle operations that should only be performed once,
        initializing the object before ordering conditions.
        For |Ordering|, the only operation is duplication of the list of conditions (if |Ordering.number| > 1).
        This methods should not be called manually.

        Parameters
        ----------
        conditions : sequence of dict
            A list of conditions, where each condition is a dictionary mapping IV names to IV values.

        Returns
        -------
        iv_name : str or tuple
            The name of the IV, for non-atomic orderings.
            Otherwise, an empty tuple.
        iv_values : tuple
            The possible values of the IV.
            Empty for atomic orderings.

        """
        self.all_conditions = self.number * list(conditions)

        return IndependentVariable((), ())

    def get_order(self, data=None):
        """
        Get an order of conditions.
        For |Ordering|, always returns the same order.

        Parameters
        ----------
        data : dict, optional
            A dictionary describing the data of the parent section.
            Unused for atomic orderings.

        Returns
        -------
        list of dict
            A list of conditions,
            where each condition is a dictionary mapping IV names to IV values.

        """
        return self.all_conditions

    @staticmethod
    def possible_orders(conditions, unique=True):
        """
        Yield all possible orders of the conditions.
        Each order is a list of dictionaries, with each dictionary representing a condition.

        Parameters
        ----------
        conditions : sequence of dict
            A list of conditions,
            where each condition is a dictionary mapping IV names to IV values.
        unique : bool, optional
            If true (the default), will only return unique orders.
            If false, some identical orders will be generated if `conditions` contains identical elements.

        """
        if unique:
            unique_orders = set(tuple(p) for p in itertools.permutations(tuple(c.items()) for c in conditions))
            for order in unique_orders:
                yield list(dict(c) for c in order)
        else:
            yield from itertools.permutations(conditions)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__dict__ == other.__dict__
        return False


class Shuffle(Ordering):
    """
    This ordering randomly shuffles the conditions.

    Parameters
    ----------
    number : int, optional
        Number of times each condition should appear (default=1).
        Conditions are duplicated *before* shuffling.
    avoid_repeats : bool, optional
        If True (default is False), no identical conditions will appear back-to-back.

    """
    def __init__(self, number=1, avoid_repeats=False):
        super().__init__(number=number)
        self.avoid_repeats = avoid_repeats

    def __repr__(self):
        return '{}(number={}, avoid_repeats={})'.format(self.__class__.__name__, self.number, self.avoid_repeats)

    def get_order(self, data=None):
        """
        Get an order of conditions.
        For |Shuffle|, returns the conditions in a random order.

        Parameters
        ----------
        data : dict, optional
            A dictionary describing the data of the parent section.
            Unused for atomic orderings.

        Returns
        -------
        list of dict
            A list of conditions,
            where each condition is a dictionary mapping IV names to IV values.

        """
        conditions = self.all_conditions.copy()
        random.shuffle(conditions)
        if self.avoid_repeats:
            while _has_repeats(conditions):
                random.shuffle(conditions)

        return conditions


class NonAtomicOrdering(Ordering):
    """
    This is a base class for non-atomic orderings, and is not meant to be directly instantiated.
    Non-atomic orderings work by creating a new independent variable one level up.
    The IV name will start with an underscore, a convention to avoid name clashes.

    """
    iv_name = 'order'

    def __init__(self, number=1):
        super().__init__(number=number)
        self.order_ivs = {}

    @property
    def iv(self):
        """
        The IV associated with the non-atomic ordering.
        It will be added to the design one level up in the experiment hierarchy.

        Returns
        -------
        iv_name : str or tuple
            The name of the IV, for non-atomic orderings.
            Otherwise, an empty tuple.
        iv_values : seq
            The possible values of the IV.
            Empty for atomic orderings.
        """
        return IndependentVariable(self.iv_name, list(self.order_ivs.keys()))

    def get_order(self, data=None):
        """
        Get an order of conditions.

        Parameters
        ----------
        data : dict, optional
            A dictionary describing the data of the parent section.

        Returns
        -------
        list of dict
            A list of conditions,
            where each condition is a dictionary mapping IV names to IV values.

        """
        return self.order_ivs[data[self.iv_name]]


class CompleteCounterbalance(NonAtomicOrdering):
    """
    In a complete counterbalance design, every unique ordering of the conditions appears the same numbers of times.

    Parameters
    ----------
    number : int, optional
        The number of times each condition should be duplicated.
        Note that conditions are duplicated *before* determining the possible orderings.

    Notes
    -----
    The number of possible orderings can get very large very quickly.
    Therefore, a complete counterbalance is not recommended for more than 3 conditions.
    The number of unique orderings can be determined by
    ``factorial(number * k) // number**k``,
    where `k` is the number of conditions (assuming all conditions are unique).
    For example, with 5 conditions there are 120 possible orders;
    with 3 conditions and ``number==2``, there are 90 unique orders.

    """
    iv_name = 'counterbalance_order'

    def first_pass(self, conditions):
        """
        Handle operations that should only be performed once,
        initializing the object before ordering conditions.
        For |CompleteCounterbalance|, all possible orders are determined.
        This method should not be called manually.

        Parameters
        ----------
        conditions : sequence of dict
            A list of conditions,
            where each condition is a dictionary mapping IV names to IV values.

        Returns
        -------
        iv_name : str or tuple
            The name of the IV to be created one level up, ``'counterbalance_order'``.
        iv_values : tuple
            Values of the IV to be created one level up,
            integers each associated with an order of the conditions.

        """
        conditions = list(conditions)
        self.all_conditions = self.number * conditions

        # Warn because this might hang if this method is accidentally used with too many possible orders.
        non_distinct_orders = factorial(len(self.all_conditions))
        equivalent_orders = factorial(self.number)**len(conditions)
        logger.warning("Creating IV '{}' with {} levels.".format(
            self.iv_name, non_distinct_orders//equivalent_orders))

        self.order_ivs = dict(enumerate(self.possible_orders(self.all_conditions)))
        return self.iv


class Sorted(NonAtomicOrdering):
    """
    Sorts the conditions based on the value of the IV defined at its level.
    This ordering can be non-atomic (if `order` ``== 'both'``),
    creating an IV with levels of ``'ascending'`` and ``'descending'``.
    If `order` is ``'ascending'`` or ``'descending'``, the ordering will be atomic
    (each section will be ordered the same way).

    Parameters
    ----------
    order : {'both', 'ascending', 'descending'}, optional
        The order to sort the sections.
        If ``'both'`` (the default),
        half the sections will be created in ascending order, and half in descending order,
        depending on the value of the new IV ``'sorted_order'``.
    number : int, optional
        The number of times each condition should appear.

    Notes
    -----
    To avoid ambiguity, |Sorted| can only be used at levels containing only one IV.

    """
    iv_name = 'sorted_order'

    def __init__(self, number=1, order='both'):
        super().__init__(number=number)
        self.order = order

    def __repr__(self):
        return "{}(number={}, order='{}')".format(self.__class__.__name__, self.number, self.order)

    def first_pass(self, conditions):
        """
        Handle operations that should only be performed once,
        initializing the object before ordering conditions.
        For |Sorted|, the conditions are sorted on IV values.

        Parameters
        ----------
        conditions : sequence of dict
            A list of conditions,
            where each condition is a dictionary mapping IV names to IV values.

        Returns
        -------
        iv_name : str or tuple
            If `order` is ``'both'``, the name of the IV to be created one level up, ``'sorted_order'``.
            Otherwise, an empty tuple (denoting that no IV will be created).
        iv_values : tuple
            If `order` is ``'both'``, values of the IV to be created one level up,
            integers each associated with an order of the conditions.
            Otherwise, empty tuple.

        """
        self.all_conditions = self.number * list(conditions)
        if len(self.all_conditions[0]) > 1:
            raise ValueError("Ordering method 'Sorted' only works with one IV")
        self.order_ivs = {'ascending': sorted(self.all_conditions,
                                              key=lambda condition: list(condition.values())[0]),
                          'descending': sorted(self.all_conditions,
                                               key=lambda condition: list(condition.values())[0],
                                               reverse=True)}

        if self.order == 'both':
            logger.warning("Creating IV '{}' with levels 'ascending' and 'descending'.".format(self.iv_name))
            return self.iv
        else:
            return IndependentVariable((), ())

    def get_order(self, data=None):
        """
        Get an order of conditions.

        Parameters
        ----------
        data : dict, optional
            A dictionary describing the data of the parent section.

        Returns
        -------
        list of dict
            A list of conditions,
            where each condition is a dictionary mapping IV names to IV values.

        """
        if self.order == 'both':
            order = data[self.iv_name]
        else:
            order = self.order
        return self.order_ivs[order]


class LatinSquare(NonAtomicOrdering):
    """
    Orders the conditions by constructing an NxN Latin square,
    where N is the number of unique conditions.
    A Latin square is a matrix with each element appearing exactly once in each row and column.
    Each row represents a different potential ordering of the conditions.
    This allows for balanced counterbalancing,
    in designs too large to accommodate a complete counterbalance.

    Parameters
    ----------
    number : int, optional
        The number of times the Latin square should be repeated (default=1).
        Duplication occurs *after* constructing the square.
    balanced : bool, optional
        If True (the default), first-order order effects will be balanced
        Each condition will appear the same number of times
        immediately before and immediately after every other condition.
        Balanced latin squares can only be constructed with an even number of conditions.
    uniform : bool, optional
        If True (default is False), the Latin square will be randomly sampled
        from a uniform distribution of Latin squares of size NxN.
        Otherwise, the sampling will be biased.
        The construction of balanced, uniform Latin squares is not implemented.

    Notes
    -----
    The algorithm for computing unbalanced Latin squares is not very efficient.
    It is not recommended to construct unbalanced, uniform Latin squares of order above 5;
    for non-uniform, unbalanced Latin squares it is safe to go up to an order of 10.
    Higher than that, computation times increase rapidly.

    The algorithm for computing balanced Latin squares is fast only because it is not robust;
    it is very biased and only samples from the same limited set of balanced Latin squares.
    However, this is usually not an issue.
    For more implementation details, see |latin_square| and |balanced_latin_square|.

    """
    iv_name = 'latin_square_row'

    def __init__(self, number=1, balanced=True, uniform=False):
        if balanced and uniform:
            raise ValueError('Cannot create a balanced, uniform Latin square')
        super().__init__(number=number)
        self.balanced = balanced
        self.uniform = uniform

    def __repr__(self):
        return '{}(number={}, balanced={}, uniform={})'.format(
            self.__class__.__name__, self.number, self.balanced, self.uniform)

    def first_pass(self, conditions):
        """
        Handle operations that should only be performed once,
        initializing the object before ordering conditions.
        For |LatinSquare|, the square is constructed.

        Parameters
        ----------
        conditions : sequence of dict
            A list of conditions,
            where each condition is a dictionary mapping IV names to IV values.

        Returns
        -------
        iv_name : str or tuple
            The name of the IV to be created one level up, ``'latin_square_row'``.
        iv_values : tuple
            Values of the IV to be created one level up,
            integers each corresponding to one row of the Latin square.

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
            logger.warning('Constructing Latin square of order {} from a {}uniform distribution...'.format(
                order, uniform_string))

            square = latin_square(order, uniform=self.uniform, reduced=not self.uniform, shuffle=not self.uniform)
            logger.warning('Latin square construction complete.')

        self.order_ivs = dict(enumerate(self.number * [self.all_conditions[i] for i in row] for row in square))

        logger.warning("Creating IV '{}' with {} levels.".format(self.iv_name, order))
        return self.iv


def _has_repeats(seq):
    return any(first == second for first, second in zip(seq[:-1], seq[1:]))


def latin_square(order, reduced=False, uniform=True, shuffle=False):
    """
    Constructs a Latin square of size `order` x `order`.
    Each row and column will contain every element of ``range(order)`` exactly once.

    Parameters
    ----------
    order : int
        Size of Latin square to construct.
    reduced : bool, optional
        If True (default is False),
        the first row and first column of the square will be the ``list(range(order))``,
        unless `shuffle` is also True.
    uniform : bool, optional
        If True (the default), the Latin square will be sampled from a uniform distribution of Latin squares.
        Set to False to relax this constraint and allow for a faster run time.
    shuffle : bool, optional
        If True (default is False),
        after construction of the Latin square its rows will be shuffled randomly,
        then its columns, and then the elements will be randomly permuted.
        Shuffling is irrelevant when `uniform` is True.
        Otherwise, it adds some randomness, though the resulting Latin square will still be biased.

    Returns
    -------
    array-like
        A Latin square of size `order` x `order`.

    See Also
    --------
    balanced_latin_square
    LatinSquare

    Notes
    -----
    This function uses a naive algorithm to construct latin squares,
    randomly generating elements and starting over whenever a collision is encountered.
    It will take a long time to construct Latin squares of order 5,
    when sampling from a uniform distribution.
    However, if a uniform distribution is not required,
    it is recommended to also set `reduced` and `shuffle` to True for fastest run times.
    In this case, latin squares up to an order of about 10 can be constructed in a reasonable amount of time.

    Examples
    --------
    >>> latin_square(5)
    [[4, 2, 0, 1, 3],
     [0, 3, 1, 4, 2],
     [3, 1, 2, 0, 4],
     [2, 0, 4, 3, 1],
     [1, 4, 3, 2, 0]]  #random

     >>> latin_square(5, reduced=True, uniform=False)
     [[0, 1, 2, 3, 4],
      [1, 2, 4, 0, 3],
      [2, 0, 3, 4, 1],
      [3, 4, 1, 2, 0],
      [4, 3, 0, 1, 2]]  #random

    """
    numbers = list(range(order))
    square = []
    if reduced:
        while not _is_latin_rect(square):
            square = [numbers]   # To get a uniform sampling of latin squares, we must start over every time.
            for row in range(1, order):
                square.append(_new_row(order, reduced_row=row))
                if uniform and not _is_latin_rect(square):
                    break
                elif not uniform:
                    while not _is_latin_rect(square):
                        square[-1] = _new_row(order, reduced_row=row)

    else:  # Not reduced.
        while not _is_latin_rect(square):
            square = []
            for _ in range(order):
                square.append(_new_row(order))
                if uniform and not _is_latin_rect(square):
                    break
                elif not uniform:
                    while not _is_latin_rect(square):
                        square[-1] = _new_row(order)

    if shuffle:
        _shuffle_latin_square(square)

    return square


def balanced_latin_square(order):
    """
    Constructs a row-balanced latin square of order `order`.
    In a row-balanced Latin square, immediate order effects are accounted for.
    Every two-element, back-to-back sequence occurs the same number of times.
    This is in addition to the standard Latin square constraint
    with every row and column containing each element exactly once.

    Parameters
    ----------
    order : int
        Order of the Latin square to construct.
        Must be even.

    Returns
    -------
    array-like
        A balanced Latin square of size `order` x `order`.

    See Also
    --------
    latin_square
    LatinSquare


    Notes
    -----
    The algorithm constructs a stereotypical balanced Latin square,
    then shuffles the rows and elements (but not the columns).
    This algorithm is much faster than the algorithm used by |latin_square|.
    However, it does not sample from a uniform distribution of balanced Latin squares (i.e. it is biased)
    and it cannot create Latin squares that are both reduced and balanced.

    Examples
    --------
    >>> balanced_latin_square(6)
    [[0, 2, 1, 5, 4, 3],
     [5, 3, 2, 4, 0, 1],
     [1, 0, 4, 2, 3, 5],
     [2, 5, 0, 3, 1, 4],
     [4, 1, 3, 0, 5, 2],
     [3, 4, 5, 1, 2, 0]]  # random

    """
    if order % 2:
        raise ValueError('Cannot compute a balanced Latin square with an odd order')

    original_numbers = range(order)
    column_starts = [0, 1]
    for first, last in zip(original_numbers[2:], reversed(original_numbers[2:])):
        column_starts.append(last)
        column_starts.append(first)
        if len(column_starts) == order:
            break

    square = []
    for start in column_starts:
        column = deque(original_numbers)
        column.rotate(-start)
        square.append(list(column))
    square = list(zip(*square))
    square = [list(row) for row in square]

    return _shuffle_latin_square(square, shuffle_columns=False)


def _shuffle_latin_square(square, shuffle_columns=True, shuffle_rows=True, shuffle_items=True):
    order = len(square)

    if shuffle_rows:
        random.shuffle(square)

    if shuffle_columns:
        square = list(zip(*square))
        random.shuffle(square)
        square = list(zip(*square))
        square = [list(row) for row in square]

    if shuffle_items:
        new_factors = list(range(order))
        random.shuffle(new_factors)
        new_square = []
        for row in square:
            new_row = row.copy()
            for original_factor, new_factor in zip(range(order), new_factors):
                new_row[row.index(original_factor)] = new_factor
            new_square.append(new_row)
        square = new_square

    assert(_is_latin_rect(square))

    return square


def _is_latin_rect(matrix):
    if not matrix:
        return False
    return (all(len(set(row)) == len(row) for row in matrix) and
            all(len(set(column)) == len(column) for column in zip(*matrix)))


def _new_row(order, reduced_row=None):
    numbers = list(range(order))
    if reduced_row is not None:
        new_row = [reduced_row]
        remaining_numbers = list(set(numbers) - set(new_row))
        random.shuffle(remaining_numbers)
        new_row.extend(remaining_numbers)

    else:
        new_row = numbers.copy()
        random.shuffle(new_row)

    return new_row


by_name = {
    'ordering': Ordering,
    'shuffle': Shuffle,
    'completecounterbalance': CompleteCounterbalance,
    'complete_counterbalance': CompleteCounterbalance,
    'counterbalance': CompleteCounterbalance,
    'counterbalanced': CompleteCounterbalance,
    'sorted': Sorted,
    'sort': Sorted,
    'latinsquare': LatinSquare,
    'latin_square': LatinSquare,
}


class OrderSchema(ClassSchema):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'n' in self.kwargs:
            self.number = self.kwargs.pop('n')

    def lookup_name(self):
        return by_name[self.name.lower()]
