"""Tests for the experimentator workflow.

Tests the process of creating an experiment, pickling it to disk, running command-line operations on it, and unpickling
it.

"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import contextmanager
from numpy import isnan
import pytest

from experimentator import load_experiment
from experimentator.cli import main
from tests.test_experiment import make_blocked_exp, check_trial


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

    main(args='exp run test.pkl --next participant'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] == 1:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp --demo run test.pkl participant 2 block 1'.split()[1:])
    for row in exp.dataframe.iterrows():
        if row[0][0] == 1:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp run test.pkl participant 2 block 1'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] == 1 or (row[0][0] == 2 and row[0][1] == 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp resume test.pkl participant'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] <= 2:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp run test.pkl --next trial'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] <= 2 or row[0] == (3, 1, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp resume test.pkl participant 3 block 1 --demo'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] <= 2 or row[0] == (3, 1, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp --debug resume test.pkl participant 3 block 1'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.dataframe.iterrows():
        if row[0][0] <= 2 or row[0][:2] == (3, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    os.remove('test.pkl')


def test_pickle_error():
    exp = make_blocked_exp()
    exp.set_context_manager('block', block_context, func_module='not_a_module')
    exp.experiment_file = 'test.pkl'
    exp.save()

    with pytest.raises(ImportError):
        main(args='exp run test.pkl --next participant'.split()[1:])


def context(data, session_data, experiment_data):
    assert session_data['options'] == 'pass,through,option'
    yield


def test_options():
    exp = make_blocked_exp()
    exp.set_context_manager('block', context)
    exp.experiment_file = 'test.pkl'
    exp.save()
    main(args='exp run test.pkl --next participant -o pass,through,option'.split()[1:])
