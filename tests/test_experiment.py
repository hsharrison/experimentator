"""Tests for Experiment object.

"""
import pytest

from experimentator.api import within_subjects_experiment, blocked_experiment, standard_experiment
from experimentator.order import Shuffle, CompleteCounterbalance
from experimentator import Design, DesignTree, Experiment


def trial(*args, a, b, **kwargs):
    return {'result': (b+1)**2 if a else b}


def make_simple_exp():
    ivs = {'a': [False, True], 'b': [0, 1, 2]}
    exp = within_subjects_experiment(ivs, 10, ordering=Shuffle(4))
    exp.set_run_callback(trial)
    return exp


def make_blocked_exp():
    exp = blocked_experiment({'a': [False, True]}, 2,
                             block_ivs={'b': [0, 1, 2]},
                             orderings={'trial': Shuffle(4), 'block': CompleteCounterbalance()})
    exp.set_run_callback(trial)
    return exp


def make_standard_exp():
    exp = standard_experiment(('participant', 'block', 'trial'),
                              {'block': [('b', [0, 1, 2])],
                               'trial': [('a', [False, True])]},
                              ordering_by_level={'trial': Shuffle(4),
                                                 'block': CompleteCounterbalance(),
                                                 'participant': Shuffle(2)})
    exp.set_run_callback(trial)
    return exp


def make_manual_exp():
    tree = DesignTree([('participant', [Design(ordering=Shuffle(2))]),
                       ('block', [Design(ivs={'b': [0, 1, 2]}, ordering=CompleteCounterbalance())]),
                       ('trial', [Design({'a': [False, True]}, ordering=Shuffle(4))]),
                       ])
    exp = Experiment(tree)
    exp.set_run_callback(trial)
    return exp


def test_construction():
    exp = make_simple_exp()
    assert exp.tree.levels_and_designs[0][0] == exp.base_section.level == '_base'
    assert exp.levels == type(exp.levels)([exp.base_section[0].level, exp.base_section[0][0].level]) \
        == type(exp.levels)(['participant', 'trial'])


def test_data_before_running():
    data = make_simple_exp().data
    assert data.shape == (2 * 3 * 4 * 10, 2)
    assert set(data.columns.values) == {'a', 'b'}
    assert data.index.names == type(data.index.names)(['participant', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*10*4*1 + 2*10*4*2

    data = make_blocked_exp().data
    assert data.shape == (2 * 3 * 4 * 6 * 2, 3)
    assert set(data.columns.values) == {'a', 'b', CompleteCounterbalance.iv_name}
    assert data.index.names == type(data.index.names)(['participant', 'block', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*6*2*4*1 + 2*6*2*4*2

    data = make_standard_exp().data
    assert data.shape == (2 * 3 * 4 * 6 * 2, 3)
    assert set(data.columns.values) == {'a', 'b', CompleteCounterbalance.iv_name}
    assert data.index.names == type(data.index.names)(['participant', 'block', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*6*2*4*1 + 2*6*2*4*2

    data = make_manual_exp().data
    assert data.shape == (2 * 3 * 4 * 6 * 2, 3)
    assert set(data.columns.values) == {'a', 'b', CompleteCounterbalance.iv_name}
    assert data.index.names == type(data.index.names)(['participant', 'block', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*6*2*4*1 + 2*6*2*4*2


def test_demo_mode():
    exp = make_simple_exp()
    exp.run_section(exp.base_section, demo=True)
    data = exp.data
    assert data.shape == (2 * 3 * 4 * 10, 2)
    assert set(data.columns.values) == {'a', 'b'}
    assert data.index.names == type(data.index.names)(['participant', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*4*10*1 + 2*4*10*2


def check_trial(row):
    assert trial({}, {}, **row[1])['result'] == row[1]['result']


def test_data_after_running():
    exp = make_simple_exp()
    exp.run_section(exp.base_section)
    for row in exp.data.iterrows():
        yield check_trial, row
    exp = make_blocked_exp()
    exp.run_section(exp.base_section)
    for row in exp.data.iterrows():
        yield check_trial, row
    assert exp.find_first_not_run('trial') is None


def test_find_section():
    exp = make_simple_exp()

    some_participant = exp.section(participant=3)
    assert not some_participant.is_bottom_level
    assert some_participant.level == 'participant'

    some_trial = exp.section(participant=4, trial=1)
    assert some_trial.is_bottom_level
    assert some_trial.level == 'trial'

    sections = list(exp.all_sections(trial=1))
    assert len(sections) == 10
    for section in sections:
        assert section.context['trial'] == 1
        assert section.is_bottom_level

    exp = make_standard_exp()
    some_trials = list(exp.all_sections(block=3, trial=[4, 8]))
    assert len(some_trials) == 2 * 6 * 2
    for section in some_trials:
        assert section.context['block'] == 3
        assert section.context['trial'] in (4, 8)

    some_trials = list(exp.all_sections(participant=3, block=[1, 3], trial=6))
    assert len(some_trials) == 2
    for section in some_trials:
        assert section.context['participant'] == 3
        assert section.context['block'] in (1, 3)
        assert section.context['trial'] == 6


def test_find_parents():
    exp = make_manual_exp()
    assert list(exp.parents(exp.section(participant=1))) == []
    assert list(exp.parents(exp.section(participant=1, block=2))) == [exp.base_section[0]]
    assert list(exp.parents(exp.section(participant=1, block=2, trial=3))) == [exp.base_section[0], exp.base_section[0][1]]


def test_find_first_not_run():
    exp = make_simple_exp()
    exp.run_section(exp.base_section[0])
    assert exp.find_first_not_run('participant') is exp.base_section[1]
    assert exp.find_first_not_run('trial') is exp.base_section[1][0]
    assert exp.find_first_not_run('trial', starting_at=exp.section(participant=1)) is None
    assert exp.find_first_not_run('trial', starting_at=exp.section(participant=2)) is exp.base_section[1][0]
    assert exp.find_first_not_run('trial', starting_at=exp.section(participant=3)) is exp.base_section[2][0]


def test_run_from():
    exp = make_blocked_exp()
    exp.run_section(exp.section(participant=1), from_section=[2, 4])
    assert not exp.section(participant=1, block=1).has_started and not exp.section(participant=1, block=1).has_finished
    assert not any(exp.section(participant=1, block=2, trial=n).has_started or
                   exp.section(participant=1, block=2, trial=n).has_finished for n in range(1, 4))
    assert all(exp.section(participant=1, block=2, trial=n).has_started and
               exp.section(participant=1, block=2, trial=n).has_finished for n in range(4, 9))
    assert exp.section(participant=1, block=3).has_started and exp.section(participant=1, block=3).has_finished
    assert not exp.section(particiapnt=2).has_started


def test_resume():
    exp = make_standard_exp()
    assert exp.find_first_partially_run('participant') is None
    exp.run_section(exp.section(participant=1, block=1))
    assert exp.section(participant=1).has_started and not exp.section(participant=1).has_finished
    assert exp.section(participant=1, block=1).has_started and exp.section(participant=1, block=1).has_finished
    assert not exp.section(participant=1, block=2).has_started and not exp.section(participant=1, block=2).has_finished
    assert exp.find_first_not_run('participant') is exp.section(participant=2)
    assert exp.find_first_not_run('participant', by_started=False) is exp.section(participant=1)
    assert exp.find_first_partially_run('participant') is exp.base_section[0]

    with pytest.raises(ValueError):
        exp.resume_section(exp.section(participant=1, block=2, trial=1))
    with pytest.raises(ValueError):
        exp.resume_section(exp.section(participant=1, block=1))
    with pytest.raises(ValueError):
        exp.resume_section(exp.section(participant=1, block=2))

    exp.resume_section(exp.section(participant=1))
    assert exp.section(participant=1).has_finished
    assert exp.find_first_not_run('participant') is exp.section(participant=2)
    assert exp.find_first_not_run('participant', by_started=False) is exp.section(participant=2)


def test_finished_section_detection():
    exp = make_manual_exp()
    exp.run_section(exp.section(participant=1, block=1))
    assert exp.section(participant=1).has_started
    exp.run_section(exp.section(participant=1, block=2))
    assert not exp.section(participant=1).has_finished
    exp.run_section(exp.section(participant=1, block=3))
    assert exp.section(participant=1).has_finished


def start_callback(level, session_data, persistent_data, **kwargs):
    if level + 's_started' in session_data:
        session_data[level + 's_started'] += 1
    else:
        session_data[level + 's_started'] = 1

    if persistent_data[level] in session_data:
        session_data[persistent_data[level]].add(kwargs[level])
    else:
        session_data[persistent_data[level]] = {kwargs[level]}


def end_callback(level, session_data, persistent_data, **kwargs):
    if level + 's_ended' in session_data:
        session_data[level + 's_ended'] += 1
    else:
        session_data[level + 's_ended'] = 1


def inter_callback(level, session_data, persistent_data, **kwargs):
    if level + 's_between' in session_data:
        session_data[level + 's_between'] += 1
    else:
        session_data[level + 's_between'] = 1


def test_callbacks_and_data():
    exp = make_blocked_exp()
    exp.set_start_callback('participant', start_callback, 'participant')
    exp.set_start_callback('block', start_callback, 'block')
    exp.set_end_callback('participant', end_callback, 'participant')
    exp.set_end_callback('block', end_callback, 'block')
    exp.set_inter_callback('participant', inter_callback, 'participant')
    exp.set_inter_callback('block', inter_callback, 'block')
    exp.set_inter_callback('trial', inter_callback, 'trial')

    exp.persistent_data.update({level: level + 's_seen' for level in ('participant', 'block')})
    exp.run_section(exp.base_section)

    assert exp.session_data['blocks_between'] == 6 * 2 * (3-1)
    assert exp.session_data['trials_between'] == 6 * 2 * 3 * (2*4 - 1)

    assert exp.session_data['participants_seen'] == set(range(1, 6*2 + 1))
    assert exp.session_data['blocks_seen'] == {1, 2, 3}

    assert exp.session_data['blocks_started'] == \
        exp.session_data['blocks_ended'] == \
        6 * 2 * 3
    assert exp.session_data['participants_started'] == \
        exp.session_data['participants_ended'] == \
        exp.session_data['participants_between'] + 1 == \
        6 * 2
