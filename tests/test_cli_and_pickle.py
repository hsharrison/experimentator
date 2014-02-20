"""Tests for the experimentator workflow.

Tests the process of creating an experiment, pickling it to disk, running command-line operations on it, and unpickling
it.

"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from numpy import isnan

from experimentator import load_experiment
from experimentator.__main__ import main
from tests.test_experiment import make_blocked_exp, check_trial


def set_session_data(session_data, persistent_data, **context):
    session_data['test'] = True


def check_session_data(session_data, persistent_data, **context):
    assert session_data['test']


def test_cli():
    exp = make_blocked_exp()
    exp.set_start_callback('participant', set_session_data)
    exp.set_inter_callback('block', check_session_data)
    exp.experiment_file = 'test.pkl'
    exp.save()

    main(args='exp run test.pkl --next participant'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.data.iterrows():
        if row[0][0] == 1:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp --demo run test.pkl participant 2 block 1'.split()[1:])
    for row in exp.data.iterrows():
        if row[0][0] == 1:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp run test.pkl participant 2 block 1'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.data.iterrows():
        if row[0][0] == 1 or (row[0][0] == 2 and row[0][1] == 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp resume test.pkl participant'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.data.iterrows():
        if row[0][0] <= 2:
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp run test.pkl --next trial'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.data.iterrows():
        if row[0][0] <= 2 or row[0] == (3, 1, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp resume test.pkl participant 3 block 1 --demo'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.data.iterrows():
        if row[0][0] <= 2 or row[0] == (3, 1, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])

    main(args='exp resume test.pkl participant 3 block 1'.split()[1:])
    exp = load_experiment('test.pkl')
    for row in exp.data.iterrows():
        if row[0][0] <= 2 or row[0][:2] == (3, 1):
            yield check_trial, row
        else:
            assert isnan(row[1]['result'])
