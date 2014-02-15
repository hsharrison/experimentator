"""Tests for Experiment object.

"""
from experimentator.api import within_subjects_experiment, blocked_experiment
from experimentator.order import Shuffle, CompleteCounterbalance


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


def test_construction():
    exp = make_simple_exp()
    assert exp.tree.levels_and_designs[0][0] == exp.base_section.level == 'base'
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

    exp = make_blocked_exp()
    some_trials = list(exp.all_sections(block=3, trial=[4, 8]))
    assert len(some_trials) == 2 * 6 * 2
    for section in some_trials:
        assert section.context['block'] == 3
        assert section.context['trial'] in (4, 8)


def test_find_first_not_run():
    exp = make_simple_exp()
    exp.run_section(exp.base_section[0])
    assert exp.find_first_not_run('participant') is exp.base_section[1]
    assert exp.find_first_not_run('trial') is exp.base_section[1][0]
