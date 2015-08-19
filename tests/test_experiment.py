"""Tests for Experiment object.

"""
from contextlib import contextmanager
import pytest

from experimentator.order import Shuffle, CompleteCounterbalance
from experimentator import Design, DesignTree, Experiment

from tests.test_design import check_equality


def trial_result(**data):
    a = data['a']
    b = data['b']
    return {'result': (b+1)**2 if a else b}


def trial(experiment, section):
    return trial_result(**section.data)


def make_simple_exp():
    ivs = {'a': [False, True], 'b': [0, 1, 2]}
    exp = Experiment.within_subjects(ivs, 10, ordering=Shuffle(4))
    exp.add_callback('trial', trial)
    return exp


def make_blocked_exp():
    exp = Experiment.blocked({'a': [False, True]}, 2,
                             block_ivs={'b': [0, 1, 2]},
                             orderings={'trial': Shuffle(4), 'block': CompleteCounterbalance()})
    exp.add_callback('trial', trial)
    return exp


def make_standard_exp():
    exp = Experiment.basic(('participant', 'block', 'trial'),
                           {'block': [('b', [0, 1, 2])],
                            'trial': [('a', [False, True])]},
                           ordering_by_level={'trial': Shuffle(4),
                                              'block': CompleteCounterbalance(),
                                              'participant': Shuffle(2)})
    exp.add_callback('trial', trial)
    return exp


def make_manual_exp():
    tree = DesignTree.new([('participant', [Design(ordering=Shuffle(2))]),
                           ('block', [Design(ivs={'b': [0, 1, 2]}, ordering=CompleteCounterbalance())]),
                           ('trial', [Design({'a': [False, True]}, ordering=Shuffle(4))]),
                           ])
    exp = Experiment.new(tree)
    exp.add_callback('trial', trial)
    return exp


def test_construction():
    exp = make_simple_exp()
    assert exp.tree.levels_and_designs[0][0] == exp.level == '_base'
    assert (exp.levels == type(exp.levels)([exp[1].level, exp[1][1].level])
            == type(exp.levels)(['participant', 'trial']))


def test_data_before_running():
    data = make_simple_exp().dataframe
    assert data.shape == (2 * 3 * 4 * 10, 2)
    assert set(data.columns.values) == {'a', 'b'}
    assert data.index.names == type(data.index.names)(['participant', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*10*4*1 + 2*10*4*2

    data = make_blocked_exp().dataframe
    assert data.shape == (2 * 3 * 4 * 6 * 2, 3)
    assert set(data.columns.values) == {'a', 'b', CompleteCounterbalance.iv_name}
    assert data.index.names == type(data.index.names)(['participant', 'block', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*6*2*4*1 + 2*6*2*4*2

    data = make_standard_exp().dataframe
    assert data.shape == (2 * 3 * 4 * 6 * 2, 3)
    assert set(data.columns.values) == {'a', 'b', CompleteCounterbalance.iv_name}
    assert data.index.names == type(data.index.names)(['participant', 'block', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*6*2*4*1 + 2*6*2*4*2

    data = make_manual_exp().dataframe
    assert data.shape == (2 * 3 * 4 * 6 * 2, 3)
    assert set(data.columns.values) == {'a', 'b', CompleteCounterbalance.iv_name}
    assert data.index.names == type(data.index.names)(['participant', 'block', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*6*2*4*1 + 2*6*2*4*2


def test_demo_mode():
    exp = make_simple_exp()
    exp.run_section(exp[1], demo=True)
    data = exp.dataframe
    assert data.shape == (2 * 3 * 4 * 10, 2)
    assert set(data.columns.values) == {'a', 'b'}
    assert data.index.names == type(data.index.names)(['participant', 'trial'])
    assert data['a'].sum() == (-data['a']).sum()
    assert sum(data['b']) == 2*4*10*1 + 2*4*10*2


def check_trial(row):
    assert trial_result(**row[1])['result'] == row[1]['result']


def test_data_after_running():
    exp = make_simple_exp()
    exp.run_section(exp)
    for row in exp.dataframe.iterrows():
        yield check_trial, row
    exp = make_blocked_exp()
    exp.run_section(exp)
    for row in exp.dataframe.iterrows():
        yield check_trial, row
    assert exp.find_first_not_run('trial') is None


def test_find_section():
    exp = make_simple_exp()

    some_participant = exp.subsection(participant=3)
    assert not some_participant.is_bottom_level
    assert some_participant.level == 'participant'

    some_trial = exp.subsection(participant=4, trial=1)
    assert some_trial.is_bottom_level
    assert some_trial.level == 'trial'

    with pytest.raises(ValueError):
        exp.subsection(participant=30)

    sections = list(exp.all_subsections(trial=1))
    assert len(sections) == 10
    for section in sections:
        assert section.data['trial'] == 1
        assert section.is_bottom_level

    exp = make_standard_exp()
    some_trials = list(exp.all_subsections(block=3, trial=[4, 8]))
    assert len(some_trials) == 2 * 6 * 2
    for section in some_trials:
        assert section.data['block'] == 3
        assert section.data['trial'] in (4, 8)

    some_trials = list(exp.all_subsections(participant=3, block=[1, 3], trial=6))
    assert len(some_trials) == 2
    for section in some_trials:
        assert section.data['participant'] == 3
        assert section.data['block'] in (1, 3)
        assert section.data['trial'] == 6


def test_find_parent():
    exp = make_manual_exp()
    assert exp.parent(exp.subsection(participant=1)) is exp
    assert exp.parent(exp.subsection(participant=1, block=2)) is exp.subsection(participant=1)
    assert exp.parent(exp.subsection(participant=1, block=2, trial=3)) is exp.subsection(participant=1, block=2)
    assert exp.parent(exp) is None


def test_find_parents():
    exp = make_manual_exp()
    assert list(exp.parents(exp.subsection(participant=1))) == [exp]
    assert list(exp.parents(exp.subsection(participant=1, block=2))) == [exp, exp[1]]
    assert list(exp.parents(exp.subsection(participant=1, block=2, trial=3))) == [exp, exp[1], exp[1][2]]


def test_find_first_not_run():
    exp = make_simple_exp()
    exp.run_section(exp[1])
    assert exp.find_first_not_run('participant') is exp[2]
    assert exp.find_first_not_run('trial') is exp[2][1]
    assert exp.subsection(participant=1).find_first_not_run('trial') is None
    assert exp.subsection(participant=2).find_first_not_run('trial') is exp[2][1]
    assert exp.subsection(participant=3).find_first_not_run('trial') is exp[3][1]
    assert exp[1].find_first_not_run('trial') is None
    assert exp[2].find_first_not_run('trial') is exp[2][1]


def test_run_from():
    exp = make_blocked_exp()
    exp.run_section(exp.subsection(participant=1), from_section=[2, 4])
    assert not exp.subsection(participant=1, block=1).has_started and not exp.subsection(participant=1, block=1).has_finished
    assert not any(exp.subsection(participant=1, block=2, trial=n).has_started or
                   exp.subsection(participant=1, block=2, trial=n).has_finished for n in range(1, 4))
    assert all(exp.subsection(participant=1, block=2, trial=n).has_started and
               exp.subsection(participant=1, block=2, trial=n).has_finished for n in range(4, 9))
    assert exp.subsection(participant=1, block=3).has_started and exp.subsection(participant=1, block=3).has_finished
    assert not exp.subsection(participant=2).has_started


def test_resume():
    exp = make_standard_exp()
    assert exp.find_first_partially_run('participant') is None
    exp.run_section(exp.subsection(participant=1, block=1))
    assert exp.subsection(participant=1).has_started and not exp.subsection(participant=1).has_finished
    assert exp.subsection(participant=1, block=1).has_started and exp.subsection(participant=1, block=1).has_finished
    assert not exp.subsection(participant=1, block=2).has_started and not exp.subsection(participant=1, block=2).has_finished
    assert exp.find_first_not_run('participant') is exp.subsection(participant=2)
    assert exp.find_first_not_run('participant', by_started=False) is exp.subsection(participant=1)
    assert exp.find_first_partially_run('participant') is exp[1]
    assert exp[1].find_first_partially_run('block') is None

    with pytest.raises(ValueError):
        exp.resume_section(exp.subsection(participant=1, block=2, trial=1))
    with pytest.raises(ValueError):
        exp.resume_section(exp.subsection(participant=1, block=1))
    with pytest.raises(ValueError):
        exp.resume_section(exp.subsection(participant=1, block=2))

    exp.resume_section(exp.subsection(participant=1))
    assert exp.subsection(participant=1).has_finished
    assert exp.find_first_not_run('participant') is exp.subsection(participant=2)
    assert exp.find_first_not_run('participant', by_started=False) is exp.subsection(participant=2)

    exp.run_section(exp.subsection(participant=2, block=1))
    exp.run_section(exp.subsection(participant=2, block=2, trial=1))
    assert exp[2].find_first_partially_run('block') is exp[2][2]


def test_finished_section_detection():
    exp = make_manual_exp()
    exp.run_section(exp.subsection(participant=1, block=1))
    assert exp.subsection(participant=1).has_started
    exp.run_section(exp.subsection(participant=1, block=2))
    assert not exp.subsection(participant=1).has_finished
    exp.run_section(exp.subsection(participant=1, block=3))
    assert exp.subsection(participant=1).has_finished


def start_callback(experiment, section):
    session_data = experiment.session_data
    experiment_data = experiment.experiment_data
    level = section.level
    data = section.data

    if level + 's_started' in session_data:
        session_data[level + 's_started'] += 1
    else:
        session_data[level + 's_started'] = 1

    if experiment_data[level] in session_data:
        session_data[experiment_data[level]].add(data[level])
    else:
        session_data[experiment_data[level]] = {data[level]}


def end_callback(experiment, section):
    session_data = experiment.session_data
    level = section.level

    if level + 's_ended' in session_data:
        session_data[level + 's_ended'] += 1
    else:
        session_data[level + 's_ended'] = 1


def inter_callback(experiment, section):
    session_data = experiment.session_data
    level = section.level

    assert session_data[level] == level
    if level + 's_between' in session_data:
        session_data[level + 's_between'] += 1
    else:
        session_data[level + 's_between'] = 1


@contextmanager
def context(experiment, section):
    data = section.data
    level = section.level

    start_callback(experiment, section)
    if data[level] > 1:
        inter_callback(experiment, section)
    yield level
    end_callback(experiment, section)


def test_callbacks_and_data():
    exp = make_blocked_exp()
    for level in ('participant', 'block', 'trial'):
        exp.add_callback(level, context, is_context=True)

    exp.experiment_data.update({level: level + 's_seen' for level in ('participant', 'block', 'trial')})
    exp.run_section(exp[1])

    assert exp.session_data['blocks_between'] == 3-1
    assert exp.session_data['trials_between'] == 3 * (2*4 - 1)

    assert exp.session_data['participants_seen'] == {1}
    assert exp.session_data['blocks_seen'] == {1, 2, 3}

    assert (exp.session_data['blocks_started'] ==
            exp.session_data['blocks_ended'] == 3)

    assert (exp.session_data['participants_started'] ==
            exp.session_data['participants_ended'] == 1)


def test_experiment_from_spec():
    spec = {
        'design':
        {
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
        },
        'data': [1, 2, 3, 4, 5],
        'file': 'test.dat',
    }
    experiment = Experiment.from_dict(spec)
    yield check_equality, experiment.filename, 'test.dat'
    yield check_equality, experiment.experiment_data, {'data': [1, 2, 3, 4, 5]}
    yield check_equality, len(experiment), 2*2*3
    participant = experiment.subsection(participant=1)
    yield check_equality, participant.level, 'participant'
    yield check_equality, len(participant), 3
    yield check_equality, participant[1].data['design'], 'practice'
    yield check_equality, participant[2].data['design'], participant[3].data['design'], 'test'
    practice_session = participant[1]
    test_session = participant[2]
    yield check_equality, practice_session.level, test_session.level, 'session'
    yield check_equality, len(practice_session), 1
    yield check_equality, len(test_session), 2
    test_block = test_session[1]
    yield check_equality, len(test_block), 2*2 + 2*3
    yield check_in, (trial.data['difficulty'] for trial in test_block[:4]), [1, 3]
    yield check_in, (trial.data['difficulty'] for trial in test_block[5:]), [5, 7]


def check_in(items, collection):
    assert set(items) - set(collection) == set()


def test_experiment_from_yaml_file():
    experiment = Experiment.from_yaml_file('tests/test.yml')
    yield check_equality, experiment.filename, 'test.dat'
    yield check_equality, experiment.experiment_data, {'data': [1, 2, 3, 4, 5]}
    yield check_equality, len(experiment), 2*2*3
    participant = experiment.subsection(participant=1)
    yield check_equality, participant.level, 'participant'
    yield check_equality, len(participant), 3
    yield check_equality, participant[1].data['design'], 'practice'
    yield check_equality, participant[2].data['design'], participant[3].data['design'], 'test'
    practice_session = participant[1]
    test_session = participant[2]
    yield check_equality, practice_session.level, test_session.level, 'session'
    yield check_equality, len(practice_session), 1
    yield check_equality, len(test_session), 2
    test_block = test_session[1]
    yield check_equality, len(test_block), 2*2 + 2*3
    yield check_in, (trial.data['difficulty'] for trial in test_block[:4]), [1, 3]
    yield check_in, (trial.data['difficulty'] for trial in test_block[5:]), [5, 7]


def test_doc_yaml():
    experiment = Experiment.from_yaml_file('tests/doctest.yml')
    assert len(experiment) == 40
    participant = experiment[1]
    assert len(participant) == 2
    first_session, second_session = participant
    assert len(first_session[1]) == len(second_session[1]) == 4
    first_experimental_section = first_session[2]
    second_experimental_section = second_session[2]
    assert len(first_experimental_section) == 60
    assert first_experimental_section[1].level == 'trial'
    assert first_experimental_section[1].is_bottom_level
    assert len(second_experimental_section) == 2
    assert second_experimental_section[1].level == 'block'
    assert len(second_experimental_section[1]) == len(second_experimental_section[2]) == 30


def test_demo_parent_has_started():
    experiment = Experiment.from_yaml_file('tests/test.yml')
    experiment.run_section(experiment[1][2], demo=True)
    assert not experiment.has_started
