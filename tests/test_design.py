"""Tests for objects in experimentator/design.py

"""
import numpy as np
from itertools import product

from experimentator import Design


def check_sequences(first, second):
    idx_combinations = set(product(range(len(first)), repeat=2)) - {(i, i) for i in range(len(first))}
    assert not any(first[one_idx] == first[another_idx] for one_idx, another_idx in idx_combinations)
    assert all(item in second for item in first)
    assert all(item in first for item in second)


def test_factorial():
    iv_names = ('a', 'b')
    iv_values = [[1, 2, 3], [1, 2]]
    conditions = [
        {'a': 1, 'b': 1},
        {'a': 1, 'b': 2},
        {'a': 2, 'b': 1},
        {'a': 2, 'b': 2},
        {'a': 3, 'b': 1},
        {'a': 3, 'b': 2},
    ]
    assert list(Design.full_cross(iv_names, iv_values)) == conditions
    d = Design(zip(iv_names, iv_values))
    d.first_pass()
    for _ in range(3):
        yield check_sequences, d.get_order(), conditions

    iv_names = ('a', 'b', 'c')
    iv_values = [[1, 2], [1, 2], [1, 2]]
    conditions = [
        {'a': 1, 'b': 1, 'c': 1},
        {'a': 1, 'b': 1, 'c': 2},
        {'a': 1, 'b': 2, 'c': 1},
        {'a': 1, 'b': 2, 'c': 2},
        {'a': 2, 'b': 1, 'c': 1},
        {'a': 2, 'b': 1, 'c': 2},
        {'a': 2, 'b': 2, 'c': 1},
        {'a': 2, 'b': 2, 'c': 2},
    ]
    assert list(Design.full_cross(iv_names, iv_values)) == conditions
    d = Design(zip(iv_names, iv_values))
    d.first_pass()
    for _ in range(3):
        yield check_sequences, d.get_order(), conditions


def order_to_array(order, iv_names):
    return [[condition[iv] for iv in iv_names] for condition in order]


def check_design_matrix(order, iv_names, iv_values, matrix):
    order_array = np.array(order_to_array(order, iv_names))
    matrix = np.array(matrix)

    # Replace design matrix values with iv values.
    unique_elements = [np.unique(column) for column in matrix.transpose()]
    new_matrix = []
    for values, uniques, column in zip(iv_values, unique_elements, matrix.transpose()):
        if values is None:
            new_matrix.append(column)
        else:
            new_column = np.array([None for _ in range(len(column))])
            for iv_value, design_matrix_value in zip(values, uniques):
                new_column[column == design_matrix_value] = iv_value
            new_matrix.append(new_column)
            matrix = np.array(new_matrix).transpose()

    assert all(row in matrix for row in order_array)
    assert all(row in order_array for row in matrix)


def test_design_matrix():
    iv_names = ('a', 'b', 'c')
    iv_values = [[1, 2], [1, 2], [1, 2]]
    conditions = [
        {'a': 1, 'b': 1, 'c': 2},
        {'a': 1, 'b': 2, 'c': 1},
        {'a': 2, 'b': 1, 'c': 1},
        {'a': 2, 'b': 2, 'c': 2},
    ]
    matrix = np.array([[-1., -1.,  1.], [1., -1., -1.], [-1.,  1., -1.], [1.,  1.,  1.]])  # pyDOE.fracfact('a b ab')
    d = Design(ivs=zip(iv_names, iv_values), design_matrix=matrix)
    d.first_pass()

    for _ in range(3):
        yield check_sequences, d.get_order(), conditions
        yield check_design_matrix, d.get_order(), iv_names, iv_values, matrix


def test_design_matrix_with_continuous_iv():
    matrix = np.array([[-1, -1],
                       [1, -1],
                       [-1, 1],
                       [1, 1],
                       [0, 0],
                       [0, 0],
                       [0, 0],
                       [0, 0],
                       [-1.41421356, 0],
                       [1.41421356,  0],
                       [0, -1.41421356],
                       [0, 1.41421356],
                       [0, 0],
                       [0, 0],
                       [0, 0],
                       [0, 0]])  # pyDOE.ccdesign(2)
    iv_names = ['a', 'b']
    iv_values = [None, None]
    d = Design(zip(iv_names, iv_values), design_matrix=matrix)
    d.first_pass()
    for _ in range(3):
        yield check_design_matrix, d.get_order(), iv_names, iv_values, matrix
