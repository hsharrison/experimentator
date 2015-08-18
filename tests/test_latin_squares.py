"""Tests for Latin squares in experimentator/common.py.

"""
from collections import Counter
from itertools import product
import numpy as np
import pytest

from experimentator.order import latin_square, balanced_latin_square

REPEATS = 2
MAX_ORDER_FOR_UNIFORM = 4
MAX_ORDER_FOR_UNIFORM_REDUCED = 5
MAX_ORDER_FOR_NON_UNIFORM = 6
MAX_ORDER_FOR_NON_UNIFORM_REDUCED = 8
MAX_ORDER_FOR_BALANCED = 10


def check_latin_square(matrix):
    assert (np.shape(matrix)[0] == np.shape(matrix)[1] and
            all(len(row) == len(set(row)) for row in matrix) and
            all(len(col) == len(set(col)) for col in np.transpose(matrix)))


def check_reduced(matrix):
    assert (list(matrix[0]) == list(range(len(matrix[0]))) and
            list(np.transpose(matrix)[0]) == list(range(len(matrix[0]))))


def check_balanced(matrix):
    order = len(matrix)
    counts = {first: Counter() for first in range(order)}
    for row in matrix:
        for first, second in zip(row[:-1], row[1:]):
            counts[first][second] += 1

    combinations = set(product(range(order), repeat=2)) - {(n, n) for n in range(order)}
    assert len({counts[first][second] for first, second in combinations}) == 1


def test_latin_squares():
    # Check uniform Latin squares.
    for order in range(2, MAX_ORDER_FOR_UNIFORM + 1):
        for _ in range(REPEATS):
            yield check_latin_square, latin_square(order)

    # Check uniform, reduced Latin squares.
    for order in range(2, MAX_ORDER_FOR_UNIFORM_REDUCED + 1):
        for _ in range(REPEATS):
            square = latin_square(order, reduced=True)
            yield check_latin_square, square
            yield check_reduced, square
            yield check_latin_square, latin_square(order, reduced=True, shuffle=True)

    # Check non-uniform Latin squares.
    for order in range(2, MAX_ORDER_FOR_NON_UNIFORM + 1):
        for shuffle in [True, False]:
            for _ in range(REPEATS):
                yield check_latin_square, latin_square(order, uniform=False, shuffle=shuffle)

    # Check non-uniform, reduced Latin squares.
    for order in range(2, MAX_ORDER_FOR_NON_UNIFORM_REDUCED + 1):
        for _ in range(REPEATS):
            square = latin_square(order, reduced=True, uniform=False)
            yield check_latin_square, square
            yield check_reduced, square
            yield check_latin_square, latin_square(order, reduced=True, uniform=False, shuffle=True)


def test_balanced_latin_squares():
    for order in range(2, MAX_ORDER_FOR_BALANCED + 1, 2):
        for _ in range(REPEATS):
            square = balanced_latin_square(order)
            yield check_latin_square, square
            yield check_balanced, square


def test_odd_balanced_latin_squares():
    for order in range(3, MAX_ORDER_FOR_BALANCED, 2):
        with pytest.raises(ValueError):
            balanced_latin_square(order)
