# Copyright (c) 2013 Henry S. Harrison

import collections
import pandas as pd

import experimentator.experimentator as exp

levels = ('trunk', 'branch', 'stem', 'leaf')
settings = {'trunk': dict(),
            'branch': dict(ivs={'a': range(2), 'b': range(3)}),
            'stem': dict(ivs={'c': ['a', 'b', 'c'], 'd': [12, 17, 61, 2.61], 'e': [True, False]},
                         sort='random',
                         n=1),
            'leaf': dict(ivs={'f': range(6)},
                         sort=list(reversed(range(6))),
                         n=2)}

n_children = dict(trunk=2*3, branch=3*4*2, stem=6*2, leaf=0)
total_branches = n_children['trunk']
total_stems = total_branches * n_children['branch']
total_leafs = total_stems * n_children['stem']


def test_tree():
    root = exp.ExperimentSection(collections.ChainMap(), levels, settings)
    yield from check_descendants(check_n_children, root)


def check_descendants(func, node):
    yield func, node
    for c in node.children:
        yield from check_descendants(func, c)


def check_n_children(node):
    assert len(node.children) == n_children[node.level]


sample_experiment = exp.Experiment(settings_by_level=settings,
                                   levels=levels)


@sample_experiment.run
def run_trial(**iv):
    branch = iv['a'] + iv['b']
    if iv['e']:
        stem = iv['c'] + str(iv['d'])
    else:
        stem = str(iv['d']) + iv['c']
    leaf = iv['f'] * 2
    return {'branch_results': branch,
            'stem_results': stem,
            'leaf_results': leaf}

sample_experiment.run_section(sample_experiment.root)
sample_data = sample_experiment.data


#noinspection PyTypeChecker
def test_experiment_data():
    assert len(sample_data) == total_leafs
    assert all(sample_data['f'] == pd.Series([5, 4, 3, 2, 1, 0] * 2 * total_stems))
    assert all(sample_data['leaf_results'] == pd.Series([10, 8, 6, 4, 2, 0] * 2 * total_stems))
    assert all(sample_data['a'] + sample_data['b'] == sample_data['branch_results'])
    for i in range(3):
        assert(sum(sample_data['b'] == i) == 2 * total_leafs//6)
