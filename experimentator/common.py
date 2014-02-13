"""This module contains objects with no clear home, that may be useful in mulitple places of `experimentator`.

This module is not visible to the user and its objects should be imported in ``__init__.py``.

"""
import random
from collections import deque


class QuitSession(BaseException):
    """An Exception indicating a 'soft' exit from a running experimental session.

    Raise this exception from inside a trial when the Python session should be exited gracefully, for example if the
    user presses a 'quit' key. The experiment file will be backed up, and any data recorded in the current session will
    be saved.

    Parameters
    ----------
    message : str
              Message to display in the terminal.

    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


def latin_square(order, reduced=False, uniform=True, shuffle=False):
    """Latin square.

    Constructs a Latin square of order `order`. Each row and column will contain every element of ``range(order)``
    exactly once.

    Arguments
    ---------
    order : int
        Size of Latin square to construct.
    reduced : bool, optional
        If True, the first row and first column of the square will be the ``list(range(order))``, unless `shuffle` is
        also True. The default is False.
    uniform : bool, optional
        If True (the default), the Latin square will be sampled from a uniform distribution of Latin squares. Set to
        False to relax this constraint and allow for a faster run time.
    shuffle : bool, optional
        If True, after construction of the Latin square its rows will be shuffled randomly, then its columns, and then
        the elements (the numbers in ``range(order)``) will be randomly rearranged. The default is False. Shuffling is
        pointless when `uniform` is True. Otherwise, it will add some randomness, though the resulting latin square will
        still be biased.

    Returns
    -------
    array-like
        A Latin square of size `order` x `order`.

    See Also
    --------
    balanced_latin_square : Balanced Latin square.

    Note
    -----
    This function uses a naive algorithm to construct latin squares, randomly generating elements and starting over
    whenever a collision is encountered. It will take a long time to construct Latin squares of order 5, when sampling
    from a uniform distribution. However, if a uniform distribution is not required, it is recommended to also set
    `reduced` and `shuffle` to True for fastest run times. In this case, latin squares up to an order of about 10 can be
    constructed in a reasonable amount of time.

    Examples
    --------
    >>>latin_square(5)
    [[4, 2, 0, 1, 3],
     [0, 3, 1, 4, 2],
     [3, 1, 2, 0, 4],
     [2, 0, 4, 3, 1],
     [1, 4, 3, 2, 0]]  #random

     >>>latin_square(5, reduced=True, uniform=False)
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
    """Balanced Latin square.

    Constructs a row-balanced latin square of order `order`. In a row-balanced Latin square, immediate order effects are
    accounted for. Every two-element, back-to-back sequence occurs the same number of times. This is in addition to the
    standard Latin square constraint of every row and column containing each element exactly once.

    Arguments
    ---------
    order : int
        Order of the Latin square to construct. Must be even.

    Returns
    -------
    array-like
        A balanced Latin square of size `order` x `order`.

    See Also
    --------
    latin_square : Unbalanced latin square.


    Notes
    -----
    The algorithm constructs a stereotypical balanced Latin square, then shuffles the rows and elements (but not the
    columns). For this reason, this algorthim is much faster than the algorithm used by `latin_square`. However, it
    cannot sample from a uniform distribution of balanced latin Squares and it cannot created Latin squares that are
    both reduced and balanced.

    Examples
    --------
    >>>balanced_latin_square(6)
    [[0, 2, 1, 5, 4, 3],
     [5, 3, 2, 4, 0, 1],
     [1, 0, 4, 2, 3, 5],
     [2, 5, 0, 3, 1, 4],
     [4, 1, 3, 0, 5, 2],
     [3, 4, 5, 1, 2, 0]]  #random

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
    return all(len(set(row)) == len(row) for row in matrix) and \
        all(len(set(column)) == len(column) for column in zip(*matrix))


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
