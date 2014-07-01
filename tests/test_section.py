"""Tests for ExperimentSection class.

"""
from collections import ChainMap
import pandas as pd
import pytest

from experimentator import Design, DesignTree
from experimentator.design import Level
from experimentator.section import ExperimentSection
from experimentator.order import Ordering

from tests.test_design import make_heterogeneous_tree


def make_tree(levels, data):
    designs = [[Design([('a', range(len(levels))), ('b', [False, True])], extra_data=data, ordering=Ordering())]
               for _ in levels]
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
    assert section.local_levels == {'block'}
    
    section.append_design_tree(make_tree(['block-test', 'trial-test'], {'foo': 'bar'}), to_start=True)
    assert section.local_levels == {'block', 'block-test'}

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


def test_repr():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    assert section == eval(repr(section))


def test_dataframe():
    data = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap()).dataframe
    assert len(data) == 3*2*3*2
    assert set(data.columns) == {'a', 'b'}
    assert int(sum(data['a'] == 0)) == int(sum(data['a'] == 1)) == int(sum(data['a'] == 2)) == 6*6//3
    assert int(sum(data['b'])) == int(sum(-data['b'])) == 6*6//2


def test_find_all_sections():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    sections = list(section.all_subsections(block=[2, 4], trial=[4, 6]))
    assert len(sections) == 4
    for subsection in sections:
        assert subsection.data['block'] in (2, 4)
        assert subsection.data['trial'] in (4, 6)


def test_heterogeneous_tree_section():
    participant = ExperimentSection(make_heterogeneous_tree(), ChainMap())
    assert participant.level == 'participant'
    assert len(participant) == 3
    practice_session = participant[1]
    test_sessions = participant[2:]
    assert practice_session.level == test_sessions[0].level == test_sessions[1].level == 'session'
    assert len(practice_session) == 1
    assert len(test_sessions[0]) == len(test_sessions[1]) == 2
    practice_block = practice_session[1]
    assert practice_block.level == 'block'
    assert practice_block.data['design'] == 'practice'
    assert practice_block.data['block'] == 1 and practice_block.data['session'] == 1
    assert len(practice_block) == 2*20
    assert all(trial.data['difficulty'] in (1, 2) for trial in practice_block)
    test_block = test_sessions[1][2]
    assert test_block.level == 'block'
    assert test_block.data['design'] == 'test'
    assert test_block.data['block'] == 2 and test_block.data['session'] == 3
    assert len(test_block) == 4*5
    assert all(trial.data['difficulty'] in (1, 3, 5, 7) for trial in test_block)


def test_breadth_first_search():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section[1][2].data['foo'] = True

    key = lambda node: node.data.get('foo', False)
    search_result = section.breadth_first_search(key)
    assert search_result == [section, section[1], section[1][2]]

    assert section.breadth_first_search(lambda node: False) == []


def test_depth_first_search():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section[1][2].data['foo'] = True

    key = lambda node: node.data.get('foo', False)
    search_result = section.depth_first_search(key)
    assert search_result == [section, section[1], section[1][2]]

    assert section.depth_first_search(lambda node: False) == []


def test_depth_first_path_search():
    section = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    section[2][1].data['foo'] = True  # Target.
    section[1][2].data['foo'] = True  # Red herring.
    section.data['bar'] = True
    section[1].data['bar'] = False

    key = lambda node: node.data.get('foo', False)
    path_key = lambda node: node.data.get('bar', False)
    search_result = section.depth_first_search(key, path_key=path_key)
    assert search_result == [section, section[2], section[2][1]]

    assert section.depth_first_search(lambda node: True, path_key=lambda node: False) == []
    assert section.depth_first_search(lambda node: False, path_key=lambda node: True) == []


def test_walk():
    session = ExperimentSection(make_tree(['session', 'block', 'trial'], {}), ChainMap())
    all_sections = [session]
    for block in session:
        all_sections.append(block)
        all_sections.extend(block)

    assert all_sections == list(session.walk())
