import random
from collections import deque


class QuitSession(BaseException):
    """
    Raised to exit the experimental session.

    Raise this exception from inside a trial when the entire session should be exited, for example if the user presses
    a 'quit' key.

    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


def latin_square(order, reduced=False, uniform=True, shuffle=False):
    numbers = list(range(order))
    square = []
    if reduced:
        while not _is_latin_rect(square):
            square = [numbers]   # To get a uniform sampling of latin squares, we must start over every time.
            for row in range(1, order):
                square.append(_new_row(order, row=row, reduced=True))
                if uniform and not _is_latin_rect(square):
                    break
                elif not uniform:
                    while not _is_latin_rect(square):
                        square[-1] = _new_row(order, row=row, reduced=True)

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


def _new_row(order, row=None, reduced=False):
    numbers = list(range(order))
    if reduced:
        new_row = [row]
        remaining_numbers = list(set(numbers) - set(new_row))
        random.shuffle(remaining_numbers)
        new_row.extend(remaining_numbers)

    else:
        new_row = numbers.copy()
        random.shuffle(new_row)

    return new_row
