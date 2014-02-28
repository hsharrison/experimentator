"""Tests for ExperimentSection class.

"""
from collections import ChainMap
import pandas as pd
import pytest

from experimentator import Design, DesignTree, ExperimentSection


def make_tree(levels, data):
    designs = [[Design([('a', range(len(levels))), ('b', [False, True])], extra_data=data)] for _ in levels]
    return DesignTree(list(zip(levels, designs)))


def test_constructor():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    assert len(section) == 3*2
    assert len(section[1]) == 3*2
    assert section.level == 'session'
    assert section[1].level == 'block'
    assert section[1][1].level == 'trial'
    assert section[1][1].is_bottom_level
    assert not section.is_bottom_level
    first_trial_data = section[1][1].data
    assert first_trial_data['block'] == first_trial_data['trial'] == 1

    assert list(reversed(section)) == [section[i] for i in reversed(range(1, 7))]
    first_block = section[1]
    second_block = section[1]
    assert first_block in section
    del section[1]
    assert first_block not in section
    assert second_block.data['block'] == 1
    section[2] = first_block
    assert first_block.data['block'] == 2

    with pytest.raises(IndexError):
        not_a_section = section[0]

    with pytest.raises(IndexError):
        not_a_section = section[0:]


def test_appending_tree():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section.append_design_tree(make_tree(['block-test', 'trial-test'], {'foo': 'bar'}), to_start=True)
    assert len(section) == 10
    assert len(section[1]) == 4
    assert len(section[5]) == 6
    assert section[1].level == 'block-test'
    assert section[1][1].level == 'trial-test'
    assert section[1].data['foo'] == 'bar'
    assert section[1][1].data['foo'] == 'bar'
    assert section[1][1].data['trial-test'] == 1
    assert section[5].data['block'] == 1
    section.append_design_tree(make_tree(['block', 'trial'], {'foo': 'bar'}), to_start=True)
    assert section[9].data['block'] == 5

    with pytest.raises(ValueError):
        section.append_design_tree(make_tree(['session', 'block', 'trial'], {}), ChainMap())


def test_append_child():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section.append_child(dict(test=True))
    yield check_test_data, section[-1]
    assert section[-1].data['block'] == 7

    section[-1].append_child(dict(tree=next(next(section.tree))))
    for trial in section[-1]:
        yield check_test_data, trial

    section[1].append_child(dict(test=True), to_start=True)
    yield check_test_data, section[1][1]
    assert len(section[1]) == 7
    assert [trial.data['trial'] for trial in section[1]] == list(range(1, 8))


def check_test_data(section):
    assert section.data['test'] is True


def test_add_data():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section.add_data(dict(test=True))
    yield check_test_data, section
    for block in section:
        yield check_test_data, block
        for trial in block:
            yield check_test_data, trial


def test_data():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    data = pd.DataFrame(section.generate_data()).set_index(['block', 'trial'])
    assert int(sum(data['a'] == 0)) == int(sum(data['a'] == 1)) == int(sum(data['a'] == 2)) == 6*6//3
    assert int(sum(data['b'])) == int(sum(-data['b'])) == 6*6//2