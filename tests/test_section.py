"""Tests for ExperimentSection class.

"""
from collections import ChainMap
import pandas as pd

from experimentator import Design, DesignTree, ExperimentSection


def make_tree(levels, context):
    designs = [[Design([('a', range(len(levels))), ('b', [False, True])], **context)] for _ in levels]
    return DesignTree(list(zip(levels, designs)))


def test_constructor():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    assert len(section) == 3*2
    assert len(section[0].children) == 3*2
    assert section.level == 'session'
    assert section[0].level == 'block'
    assert section.children[0].children[0].level == 'trial'
    assert section.children[0][0].is_bottom_level
    assert not section.is_bottom_level
    first_trial_context = section[0][0].context
    assert first_trial_context['block'] == first_trial_context['trial'] == 1


def test_appending_tree():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section.append_design_tree(make_tree(['block-test', 'trial-test'], {'foo': 'bar'}), to_start=True)
    assert len(section) == 10
    assert len(section[0]) == 4
    assert len(section.children[4]) == 6
    assert section[0].level == 'block-test'
    assert section.children[0][0].level == 'trial-test'
    assert section[0].context['foo'] == 'bar'
    assert section[0][0].context['foo'] == 'bar'
    assert section.children[0][0].context['trial-test'] == 1
    assert section[4].context['block'] == 1
    section.append_design_tree(make_tree(['block', 'trial'], {'foo': 'bar'}), to_start=True)
    assert section[8].context['block'] == 5


def test_append_child():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section.append_child(context={'test': True})
    yield check_test_context, section[-1]
    assert section[-1].context['block'] == 7

    section[-1].append_child(tree=next(next(section.tree)))
    for trial in section[-1]:
        yield check_test_context, trial

    section[0].append_child(context={'test': True}, to_start=True)
    yield check_test_context, section[0][0]
    assert len(section[0]) == 7
    assert [trial.context['trial'] for trial in section[0]] == list(range(1, 8))


def check_test_context(section):
    assert section.context['test'] is True


def test_add_data():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section.add_data(test=True)
    yield check_test_context, section
    for block in section:
        yield check_test_context, block
        for trial in block:
            yield check_test_context, trial


def test_data():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    data = pd.DataFrame(section.generate_data()).set_index(['block', 'trial'])
    assert int(sum(data['a'] == 0)) == int(sum(data['a'] == 1)) == int(sum(data['a'] == 2)) == 6*6//3
    assert int(sum(data['b'])) == int(sum(-data['b'])) == 6*6//2