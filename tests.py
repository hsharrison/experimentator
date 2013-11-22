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


class SampleExperiment(exp.Experiment):
    def run_trial(self, **iv):
        branch = iv['a'] + iv['b']
        if iv['e']:
            stem = iv['c'] + str(iv['d'])
        else:
            stem = str(iv['d']) + iv['c']
        leaf = iv['f'] * 2
        return branch, stem, leaf

sample_experiment = SampleExperiment(settings,
                                     levels=levels,
                                     output_names=('branch_results', 'stem_results', 'leaf_results'))
sample_experiment.run(sample_experiment.root)
sample_data = sample_experiment.data


#noinspection PyTypeChecker
def test_experiment_data():
    assert len(sample_data) == total_leafs
    assert all(sample_data['f'] == pd.Series([5, 4, 3, 2, 1, 0] * 2 * total_stems))
    assert all(sample_data['leaf_results'] == pd.Series([10, 8, 6, 4, 2, 0] * 2 * total_stems))
    assert all(sample_data['a'] + sample_data['b'] == sample_data['branch_results'])
    assert all(sample_data['a'] == pd.Series(total_leafs//2 * [0] + total_leafs//2 * [1]))
    assert all(sample_data['b'] == pd.Series((total_leafs//6 * [0] + total_leafs//6 * [1] + total_leafs//6 * [2]) * 2))
