"""Tests for the experimentator workflow.

Tests the process of creating an experiment, pickling it to disk, running command-line operations on it, and unpickling
it.

"""
import sys
import os
import filecmp
from glob import glob
from contextlib import contextmanager
from numpy import isnan
import pytest

from experimentator import load_experiment, run_experiment_section, QuitSession, Experiment, DesignTree, Design
from experimentator.api import standard_experiment
from experimentator.cli import main
from experimentator.order import Ordering
from tests.test_experiment import make_blocked_exp, check_trial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def call_cli(args):
    main(args=args.split()[1:])


def set_session_data(data, session_data, **_):
    session_data['test'] = True


def check_session_data(data, session_data, **_):
    assert session_data['test']


@contextmanager
def participant_context(data, session_data, **_):
    session_data['test'] = True
    yield


def block_context(data, session_data, **_):
    if data['block'] > 1:
        assert session_data['test']
    yield


def test_cli():
    exp = make_blocked_exp()
    exp.set_context_manager('participant', participant_context, already_contextmanager=True)
    exp.set_context_manager('block', block_context)
    exp.experiment_file = 'test.pkl'
    exp.save()

    call_cli('exp run test.pkl --next participant')
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] == 1:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    call_cli('exp --demo run test.pkl participant 2 block 1')
    for row in exp.dataframe.iterrows():
        if row[0][0] == 1:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    call_cli('exp run test.pkl participant 2 block 1')
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] == 1 or (row[0][0] == 2 and row[0][1] == 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    call_cli('exp resume test.pkl participant')
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] <= 2:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    call_cli('exp run test.pkl --next trial')
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] <= 2 or row[0] == (3, 1, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    call_cli('exp resume test.pkl participant 3 block 1 --demo')
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] <= 2 or row[0] == (3, 1, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    call_cli('exp --debug resume test.pkl participant 3 block 1')
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] <= 2 or row[0][:2] == (3, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    for file in glob('test.pkl*'):
        os.remove(file)


def test_pickle_error():
    exp = make_blocked_exp()
    exp.set_context_manager('block', block_context, func_module='not_a_module')
    exp.experiment_file = 'test.pkl'
    exp.save()

    with pytest.raises(ImportError):
        call_cli('exp run test.pkl --next participant')


def context(data, session_data, experiment_data):
    assert session_data['options'] == 'pass,through,option'
    yield


def test_options():
    exp = make_blocked_exp()
    exp.set_context_manager('block', context)
    exp.experiment_file = 'test.pkl'
    exp.save()
    call_cli('exp run test.pkl --next participant -o pass,through,option')


def make_deterministic_exp():
    standard_experiment(('participant', 'block', 'trial'),
                        {'block': {'b': [0, 1, 2]}, 'trial': {'a': [False, True]}},
                        ordering_by_level={'trial': Ordering(4),
                                           'block': Ordering(4),
                                           'participant': Ordering()},
                        experiment_file='test.pkl').save()


def test_export():
    make_deterministic_exp()
    call_cli('exp export test.pkl test.csv')
    assert filecmp.cmp('tests/test_data.csv', 'test.csv')
    os.remove('test.csv')

    call_cli('exp export --no-index-label test.pkl test.csv')
    assert filecmp.cmp('tests/test_data_no_index_label.csv', 'test.csv')
    os.remove('test.csv')

    call_cli('exp export test.pkl test.csv --skip counterbalance_order')
    assert filecmp.cmp('tests/test_data_skip_order.csv', 'test.csv')
    os.remove('test.csv')

    for file in glob('test.pkl*'):
        os.remove(file)


def bad_trial(data, **_):
    raise QuitSession('Nope!')


def test_exception():
    exp = make_blocked_exp()
    exp.set_run_callback(bad_trial)
    exp.save()
    exp.save('test.pkl')
    with pytest.raises(QuitSession):
        run_experiment_section('test.pkl', participant=1)

    exp = load_experiment('test.pkl')
    assert exp.subsection(participant=1, block=1, trial=1).has_started
    assert not exp.subsection(participant=1, block=1, trial=1).has_finished
    os.remove('test.pkl')

    e = QuitSession('message')
    assert e.__str__() == 'message'
    with pytest.raises(QuitSession):
        raise e


def test_exp_repr():
    make_deterministic_exp()
    e = load_experiment('test.pkl')
    assert e == eval(e.__repr__())
    for file in glob('test.pkl*'):
        os.remove(file)
