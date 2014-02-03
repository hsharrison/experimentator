# Copyright (c) 2013-2014 Henry S. Harrison
from collections import ChainMap

from experimentator import Experiment
from experimentator.section import ExperimentSection
from experimentator.orderings import Shuffle


levels = ('trunk', 'branch', 'stem', 'leaf')
settings = {'trunk': dict(),
            'branch': dict(ivs={'a': range(2), 'b': range(3)}),
            'stem': dict(ivs={'c': ['a', 'b', 'c'], 'd': [12, 17, 61, 2.61], 'e': [True, False]},
                         ordering=Shuffle()),
            'leaf': dict(ivs={'f': range(6)},
                         ordering=Shuffle(2))}

n_children = dict(trunk=2*3, branch=3*4*2, stem=6*2, leaf=0)
total_branches = n_children['trunk']
total_stems = total_branches * n_children['branch']
total_leafs = total_stems * n_children['stem']


def test_tree():
    root = ExperimentSection(ChainMap(), levels, settings)
    yield from check_descendants(check_n_children, root)


def check_descendants(func, node):
    yield func, node
    for c in node.children:
        yield from check_descendants(func, c)


def check_n_children(node):
    assert len(node.children) == n_children[node.level]


sample_experiment = Experiment(settings_by_level=settings,
                               levels=levels)


def run_trial(*_, **iv):
    branch = iv['a'] + iv['b']
    if iv['e']:
        stem = iv['c'] + str(iv['d'])
    else:
        stem = str(iv['d']) + iv['c']
    leaf = iv['f'] * 2
    return {'branch_results': branch,
            'stem_results': stem,
            'leaf_results': leaf}


sample_experiment.run_callback = run_trial
sample_experiment.run_section(sample_experiment.base_section)
sample_data = sample_experiment.data


#noinspection PyTypeChecker
def test_experiment_data():
    assert len(sample_data) == total_leafs
    assert all(sample_data['leaf_results'] == 2*sample_data['f'])
    assert all(sample_data['branch_results'] == sample_data['a'] + sample_data['b'])
    assert all(sample_data['a'] + sample_data['b'] == sample_data['branch_results'])
    for i in range(3):
        assert sum(sample_data['b'] == i) == 2 * total_leafs//6
