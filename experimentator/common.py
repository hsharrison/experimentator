# Copyright (c) 2014 Henry S. Harrison
import random


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
        # Randomly permute rows.
        random.shuffle(square)
        # Randomly permute columns.
        square = list(zip(*square))
        random.shuffle(square)
        square = list(zip(*square))
        square = [list(row) for row in square]
        # Randomly assign factors.
        new_factors = list(range(order))
        random.shuffle(new_factors)
        new_square = []
        for row in square:
            new_row = row.copy()
            for original_factor, new_factor in zip(range(order), new_factors):
                new_row[row.index(original_factor)] = new_factor
            new_square.append(new_row)

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
