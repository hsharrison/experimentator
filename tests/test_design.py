"""Tests for objects in experimentator/design.py

"""
from collections import OrderedDict
from itertools import product
import pytest
import numpy as np

from experimentator import Design, DesignTree
from experimentator.order import Shuffle, Ordering, CompleteCounterbalance, Sorted


def make_immutable(list_of_dicts):
    for element in list_of_dicts:
        yield tuple(element.items())


def check_joint(first, second):
    if isinstance(first[0], dict):
        first = make_immutable(first)
        second = make_immutable(second)
    assert not set(tuple(first)).symmetric_difference(set(tuple(second)))


def check_sequences(first, second):
    idx_combinations = set(product(range(len(first)), repeat=2)) - {(i, i) for i in range(len(first))}
    assert not any(first[one_idx] == first[another_idx] for one_idx, another_idx in idx_combinations)
    check_joint(first, second)


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

    yield check_joint, matrix, order_array


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


def check_design(design, iv_names, iv_values, n, data, matrix):
    assert set(design.iv_names) == set(iv_names)
    assert len(design.get_order(data)) == n

    ivs = dict(zip(iv_names, iv_values))
    for condition in design.get_order(data):
        for iv, value in condition.items():
            if matrix is not None:
                assert value in matrix
            else:
                assert value in ivs[iv]


def check_identity(first, second):
    assert first is second


def check_equality(*items):
    try:
        first_item = items[0]
    except TypeError:
        first_item = next(items)
    assert all(item == first_item for item in items)


def test_design_tree():
    trial_matrix = np.array([[-1, -1],
                             [1, -1],
                             [-1, 1],
                             [1, 1],
                             [0, 0],
                             [0, 0],
                             [0, 0],
                             [0, 0],
                             [-1.41421356, 0.1],
                             [1.41421356,  0.1],
                             [0, -1.41421356],
                             [0, 1.41421356],
                             [0, 0],
                             [0, 0],
                             [0, 0],
                             [0, 0]])  # pyDOE.ccdesign(2) with two 0.1 elements to prevent symmetry in the IVs.
    trial_iv_names = ['a', 'b']
    trial_iv_values = [None, None]
    block_ivs = {'block': [1, 2]}
    participant_iv_names = ('A', 'B')
    participant_iv_values = [[1, 2], [1, 2, 3]]

    trial_design = Design(ivs=zip(trial_iv_names, trial_iv_values), ordering=Shuffle(3), design_matrix=trial_matrix)
    block_design = Design(block_ivs, ordering=CompleteCounterbalance())
    practice_block_design = Design()
    participant_design = Design(dict(zip(participant_iv_names, participant_iv_values)), ordering=Ordering(10))

    levels_and_designs = OrderedDict([('participant', participant_design),
                                      ('block', [practice_block_design, block_design]),
                                      ('trial', trial_design)])

    tree = DesignTree.new(levels_and_designs)
    tree.add_base_level()

    levels, designs = zip(*tree.levels_and_designs)

    yield check_identity, designs[1][0], participant_design
    yield check_identity, designs[2][0], practice_block_design
    yield check_identity, designs[2][1], block_design
    yield check_identity, designs[3][0], trial_design

    yield check_equality, len(tree), 4
    yield check_equality, tree[3], ('trial', [trial_design])

    yield check_equality, next(tree).levels_and_designs, next(tree).levels_and_designs, tree.levels_and_designs[1:]
    tree_with_participant_base = next(tree)
    tree_with_block_base = next(tree_with_participant_base)
    yield (check_equality,
           tree_with_block_base.levels_and_designs,
           next(next(tree)).levels_and_designs,
           [('block', [practice_block_design, block_design]), ('trial', [trial_design])])
    tree_with_trial_base = next(tree_with_block_base)
    yield (check_equality,
           tree_with_trial_base.levels_and_designs,
           [('trial', [trial_design])],
           next(tree_with_block_base).levels_and_designs)
    with pytest.raises(StopIteration):
        next(tree_with_trial_base)

    for design, iv_names, iv_values, n, data, matrix in zip(
            [designs[1][0], designs[2][0], designs[2][1], designs[3][0]],
            [['A', 'B', CompleteCounterbalance.iv_name], [], ['block'], ['a', 'b']],
            [[[1, 2], [1, 2, 3], [0, 1]], [], [[1, 2]], [None, None]],
            [10*2*2*3, 1, 2, 3*len(trial_matrix)],
            [{}, {}, {CompleteCounterbalance.iv_name: 0}, {}],
            [None, None, None, trial_matrix]):
        yield check_design, design, iv_names, iv_values, n, data, matrix

    yield check_design_matrix, designs[3][0].get_order(), ['a', 'b'], [None, None], trial_matrix


def check_length(sequence, n):
    assert len(sequence) == n


def check_type(object_, type_):
    assert isinstance(object_, type_)


def make_heterogeneous_tree():
    main_structure = [
        ('participant', Design(ivs={'a': [1, 2], 'b': [1, 2]}, ordering=Shuffle(3))),
        ('session', Design(ivs={'design': ['practice', 'test']}, design_matrix=[[0], [1], [1]])),
    ]
    other_structures = {
        'practice': [
            ('block', Design()),
            ('trial', Design(ivs={'difficulty': [1, 2]}, ordering=Shuffle(20))),
        ],
        'test': [
            ('block', Design(ordering=Ordering(2))),
            ('trial', Design(ivs={'difficulty': [1, 3, 5, 7]}, ordering=Shuffle(5))),
        ],
    }

    return DesignTree.new(main_structure, **other_structures)


def test_heterogeneous_design_tree():
    tree = make_heterogeneous_tree()
    try:
        while True:
            yield check_equality, next(tree), next(tree)
            tree = next(tree)
            if isinstance(tree, dict):
                tree = list(tree.values())[0]

    except StopIteration:
        pass

    tree = make_heterogeneous_tree()
    yield check_length, tree, 4
    participant = next(tree)
    yield check_length, participant, 3
    sessions = next(participant)
    yield check_type, sessions, dict
    yield check_length, sessions, 2
    yield check_length, sessions['practice'], 2
    yield check_length, sessions['test'], 2
    yield check_equality, sessions['practice'].levels_and_designs[0][0], 'block'
    yield check_equality, sessions['test'].levels_and_designs[0][0], 'block'
    practice_block = next(sessions['practice'])
    test_block = next(sessions['test'])
    yield check_equality, practice_block.levels_and_designs[0][0], 'trial'
    yield check_equality, test_block.levels_and_designs[0][0], 'trial'


def test_bad_heterogeneity():
    main_structure = [
        ('participant', Design(ivs={'a': [1, 2], 'b': [1, 2]}, ordering=Shuffle(3))),
        ('session', Design(ivs={'design': ['practice', 'test']}, design_matrix=[[0], [1], [1]])),
    ]
    other_structures = {
        'practice': [
            ('block', Design()),
            ('trial', Design(ivs={'difficulty': [1, 2]}, ordering=Shuffle(20))),
        ],
        'test': [
            ('block', Design(ordering=CompleteCounterbalance(2))),
            ('trial', Design(ivs={'difficulty': [1, 3, 5, 7]}, ordering=Shuffle(5))),
        ],
    }
    with pytest.raises(ValueError):
        DesignTree.new(main_structure, **other_structures)


def test_bad_design_matrix():
    with pytest.raises(TypeError):
        design = Design(ivs=[('a', [1]), ('b', [1])], design_matrix=np.ones((3, 3)))
        design.first_pass()


def test_continuous_ivs_without_design_matrix():
    with pytest.raises(TypeError):
        Design(ivs=[('a', None)])


def test_different_bad_design_matrix():
    iv_names = ('a', 'b', 'c')
    iv_values = [[1, 2], [1, 2, 3], [1, 2]]
    matrix = np.array([[-1., -1.,  1.], [1., -1., -1.], [-1.,  1., -1.], [1.,  1.,  1.]])  # pyDOE.fracfact('a b ab')
    d = Design(ivs=zip(iv_names, iv_values), design_matrix=matrix)
    with pytest.raises(ValueError):
        d.first_pass()


def test_design_from_spec():
    spec = {
        'name': 'test1',
        'order': 'Shuffle',
        'n': 2,
        'ivs': {'a': [True, False], 'b': [1, 2, 3]},
    }
    assert Design.from_dict(spec) == ('test1', Design({'a': [True, False], 'b': [1, 2, 3]}, ordering=Shuffle(2)))

    spec = {
        'name': 'test2',
        'some_extra_field': ['blah'],
        'number': 3,
    }
    assert Design.from_dict(spec) == ('test2', Design(extra_data={'some_extra_field': ['blah']}, ordering=Shuffle(3)))

    spec = {
        'name': 'test3',
        'ordering': {
            'class': 'Sorted',
            'order': 'ascending',
        },
        'ivs': {'a': [1, 2, 3]},
    }
    assert Design.from_dict(spec) == ('test3', Design(ivs={'a': [1, 2, 3]}, ordering=Sorted(order='ascending')))

    spec = {
        'name': 'test4',
        'order': ['CompleteCounterbalance', 3],
    }
    assert Design.from_dict(spec) == ('test4', Design(ordering=CompleteCounterbalance(3)))

    spec.pop('name')
    assert Design.from_dict(spec) == Design(ordering=CompleteCounterbalance(3))


def test_design_tree_from_spec():
    spec = {
        'main':
        [
            {
                'name': 'participant',
                'ivs': {'a': [1, 2], 'b': [1, 2]},
                'number': 3,
                'ordering': 'Shuffle',
            },
            {
                'name': 'session',
                'ivs': {'design': ['practice', 'test']},
                'design_matrix': [[0], [1], [1]],
            },
        ],
        'practice':
        [
            {
                'name': 'block'
            },
            {
                'name': 'trial',
                'ivs': {'difficulty': [1, 2]},
                'n': 2,
                'order': 'Shuffle',
            },
        ],
        'test':
        [
            {
                'name': 'block',
                'n': 2,
            },
            [
                {
                    'name': 'trial',
                    'ivs': {'difficulty': [1, 3]},
                    'number': 2,
                    'order': 'Shuffle',
                },
                {
                    'ivs': {'difficulty': [5, 7]},
                    'n': 3,
                    'order': 'Shuffle',
                },
            ],
        ],
    }
    tree = DesignTree.from_spec(spec)
    yield check_length, tree, 4
    participant = next(tree)
    yield check_length, participant, 3
    sessions = next(participant)
    yield check_type, sessions, dict
    yield check_length, sessions, 2
    yield check_length, sessions['practice'], 2
    yield check_length, sessions['test'], 2
    yield check_equality, sessions['practice'].levels_and_designs[0][0], 'block'
    yield check_equality, sessions['test'].levels_and_designs[0][0], 'block'
    practice_block = next(sessions['practice'])
    test_block = next(sessions['test'])
    yield check_equality, practice_block.levels_and_designs[0][0], 'trial'
    yield check_equality, test_block.levels_and_designs[0][0], 'trial'


def test_bad_design_tree_spec():
    spec = {
        'main':
        [
            {
                'name': 'participant',
                'ivs': {'a': [1, 2], 'b': [1, 2]},
                'number': 3,
                'ordering': 'Shuffle',
            },
            {
                'name': 'session',
                'ivs': {'design': ['practice', 'test']},
                'design_matrix': [[0], [1], [1]],
            },
        ],
        'practice':
        [
            {
                'name': 'block'
            },
            {
                'name': 'trial',
                'ivs': {'difficulty': [1, 2]},
                'n': 2,
                'order': 'Shuffle',
            },
        ],
        'test':
        [
            {
                'name': 'block',
                'n': 2,
            },
            [
                {
                    'name': 'trial',
                    'ivs': {'difficulty': [1, 3]},
                    'number': 2,
                    'order': 'Shuffle',
                },
                {
                    'name': 'not-trial',
                    'ivs': {'difficulty': [5, 7]},
                    'n': 3,
                    'order': 'Shuffle',
                },
            ],
        ],
    }
    with pytest.raises(ValueError):
        DesignTree.from_spec(spec)


def test_simple_design_tree_spec():
    spec = [
        {
            'name': 'participant',
            'ivs': {'a': [1, 2], 'b': [1, 2]},
            'number': 3,
            'ordering': 'Shuffle',
        },
        {
            'ivs': {'type': ['over', 'under']},
            'design_matrix': [[0], [1], [1]],
        },
    ]
    tree = DesignTree.from_spec(spec)
    yield check_length, tree, 2
    yield check_equality, next(tree), next(tree)
    participant = next(tree)
    yield check_length, participant, 1
    yield check_equality, participant.levels_and_designs[0][0], None


def test_bizarre_equality():
    design = Design()
    assert (design == 1) is False
    tree = DesignTree.new([('a', design)])
    assert (tree == 1) is False
