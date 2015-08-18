"""Tests for experimentator.order.

"""
from math import factorial
from itertools import product
import pytest

from experimentator.order import Shuffle, LatinSquare, Ordering, CompleteCounterbalance, Sorted, OrderSchema

CONDITIONS_3 = [{'a': c} for c in range(3)]

CONDITIONS_6 = [{'a': c} for c in range(6)]

CONDITIONS_2_2 = [{'a': 1, 'b': 1},
                  {'a': 1, 'b': 2},
                  {'a': 2, 'b': 1},
                  {'a': 2, 'b': 2}]

CONDITIONS_WITH_REPEAT = [{'a': 1, 'b': 1},
                          {'a': 1, 'b': 2},
                          {'a': 2, 'b': 1},
                          {'a': 2, 'b': 2},
                          {'a': 2, 'b': 2}]

CONDITIONS_2_3_2 = [{'a': 1, 'b': 10, 'c': False},
                    {'a': 1, 'b': 10, 'c': True},
                    {'a': 1, 'b': 20, 'c': False},
                    {'a': 1, 'b': 20, 'c': True},
                    {'a': 1, 'b': 30, 'c': False},
                    {'a': 1, 'b': 30, 'c': True},
                    {'a': 2, 'b': 10, 'c': False},
                    {'a': 2, 'b': 10, 'c': True},
                    {'a': 2, 'b': 20, 'c': False},
                    {'a': 2, 'b': 20, 'c': True},
                    {'a': 2, 'b': 30, 'c': False},
                    {'a': 2, 'b': 30, 'c': True}]

CONDITIONS_2_3 = [{'a': 1, 'b': 10},
                  {'a': 1, 'b': 20},
                  {'a': 1, 'b': 30},
                  {'a': 2, 'b': 10},
                  {'a': 2, 'b': 20},
                  {'a': 2, 'b': 30}]


def check_ordering(o, n_conditions):
    assert len(o.get_order()) == n_conditions * o.number
    assert o.get_order() == o.get_order()


def test_ordering():
    for n in range(1, 6, 2):
        for conditions in (CONDITIONS_3, CONDITIONS_6, CONDITIONS_2_3, CONDITIONS_2_3_2):
            o = Ordering(n)
            o.first_pass(conditions)
            yield check_ordering, o, len(conditions)


def test_ordering_generator_condition():
    n = 3
    o = Ordering(n)
    o.first_pass(c for c in CONDITIONS_3)
    yield check_ordering, o, len(CONDITIONS_3)


def check_shuffle(o, n_conditions):
    assert len(o.get_order()) == n_conditions * o.number
    # It is technically possible to get the same order twice. But for three to be equal? Very unlikely.
    # Specifically this test has a 0.00019 % change of failing with the 6-condition n=1 test case.
    assert not o.get_order() == o.get_order() == o.get_order()


def check_repeats(conditions):
    assert not any(first == second for first, second in zip(conditions[:-1], conditions[1:]))


def test_shuffle():
    for n in range(1, 6, 2):
        for conditions in (CONDITIONS_6, CONDITIONS_2_3, CONDITIONS_2_3_2):
            o = Shuffle(number=n)
            o.first_pass(conditions)
            yield check_shuffle, o, len(conditions)

            o = Shuffle(n, avoid_repeats=True)
            o.first_pass(conditions)
            yield check_shuffle, o, len(conditions)
            yield check_repeats, o.get_order()


def test_shuffle_generator_condition():
    n = 3
    o = Shuffle(number=n)
    o.first_pass(c for c in CONDITIONS_3)
    yield check_shuffle, o, len(CONDITIONS_3)

    o = Shuffle(n, avoid_repeats=True)
    o.first_pass(c for c in CONDITIONS_3)
    yield check_shuffle, o, len(CONDITIONS_3)
    yield check_repeats, o.get_order()


def check_unique(o, iv_values):
    iv_combinations = set(product(iv_values, repeat=2)) - {(iv_value, iv_value) for iv_value in iv_values}
    assert not any(o.get_order({o.iv_name: one_iv_value}) == o.get_order({o.iv_name: another_iv_value})
                   for one_iv_value, another_iv_value in iv_combinations)


def check_counterbalance_number(o, n_conditions, iv_values, n_repeats):
    assert len(iv_values) == factorial(o.number * n_conditions) // (factorial(n_repeats) * o.number**n_conditions)


def test_counterbalance():
    for n in range(1, 3):
        o = CompleteCounterbalance(n)
        _, iv_values = o.first_pass(CONDITIONS_3)
        yield check_unique, o, iv_values
        yield check_counterbalance_number, o, len(CONDITIONS_3), iv_values, 1

    o = CompleteCounterbalance()
    _, iv_values = o.first_pass(CONDITIONS_2_2)
    yield check_unique, o, iv_values
    yield check_counterbalance_number, o, len(CONDITIONS_2_2), iv_values, 1

    o = CompleteCounterbalance()
    _, iv_values = o.first_pass(CONDITIONS_WITH_REPEAT)
    yield check_unique, o, iv_values
    yield check_counterbalance_number, o, len(CONDITIONS_WITH_REPEAT), iv_values, 2


def test_counterbalance_generator_condition():
    n = 2
    o = CompleteCounterbalance(n)
    _, iv_values = o.first_pass(c for c in CONDITIONS_3)
    yield check_unique, o, iv_values
    yield check_counterbalance_number, o, len(CONDITIONS_3), iv_values, 1


def check_sorted(o, n_conditions):
    assert len(o.get_order({o.iv_name: 'ascending'})) == n_conditions * o.number
    if o.order == 'both':
        print(o.iv_name)
        assert o.get_order({o.iv_name: 'ascending'}) == list(reversed(o.get_order({o.iv_name: 'descending'})))
    elif o.order == 'ascending':
        assert o.get_order() == o.get_order()
        assert sorted(o.get_order(), key=lambda x: list(x.values())[0]) == o.get_order()
    elif o.order == 'descending':
        assert o.get_order() == o.get_order()
        assert sorted(o.get_order(), key=lambda x: list(x.values())[0], reverse=True) == o.get_order()


def test_sorted():
    for n in range(1, 3):
        for conditions in (CONDITIONS_3, CONDITIONS_6):
            for sort in ('both', 'ascending', 'descending'):
                o = Sorted(n, order=sort)
                o.first_pass(conditions)
                yield check_sorted, o, len(conditions)

    for conditions in (CONDITIONS_2_2, CONDITIONS_2_3, CONDITIONS_2_3_2):
        with pytest.raises(ValueError):
            o = Sorted()
            o.first_pass(conditions)


def test_sorted_generator_condition():
    n = 2
    for sort in ('both', 'ascending', 'descending'):
        o = Sorted(n, order=sort)
        o.first_pass(c for c in CONDITIONS_3)
        yield check_sorted, o, len(CONDITIONS_3)


def check_latin_square_row(row):
    assert not any(first == second for first, second in zip(row[:-1], row[1:]))


def test_latin_square():
    for conditions in (CONDITIONS_2_2, CONDITIONS_3):
        for uniform in (True, False):
            for balanced in (True, False):
                if balanced and uniform:
                    with pytest.raises(ValueError):
                        LatinSquare(balanced=balanced, uniform=uniform)
                else:
                    o = LatinSquare(balanced=balanced, uniform=uniform)
                    if balanced and len(conditions) % 2:
                        with pytest.raises(ValueError):
                            o.first_pass(conditions)
                    else:
                        iv_name, iv_values = o.first_pass(conditions)
                        yield check_unique, o, iv_values
                        for iv_value in iv_values:
                            yield check_latin_square_row, o.get_order({iv_name: iv_value})


def test_latin_square_generator_condition():
    uniform = False
    balanced = False
    o = LatinSquare(balanced=balanced, uniform=uniform)
    iv_name, iv_values = o.first_pass(c for c in CONDITIONS_3)
    yield check_unique, o, iv_values
    for iv_value in iv_values:
        yield check_latin_square_row, o.get_order({iv_name: iv_value})


def test_latin_square_repeat():
    o = LatinSquare(2)
    iv_name, iv_values = o.first_pass(CONDITIONS_2_2)
    yield check_unique, o, iv_values
    for iv_value in iv_values:
        ord = o.get_order({iv_name: iv_value})
        assert ord[:len(ord)//2] == ord[len(ord)//2:]
        yield check_latin_square_row, ord[:len(ord)//2]


def check_repr(obj):
    assert obj == eval(repr(obj))


def test_reprs():
    for ord in (CompleteCounterbalance(), Shuffle(), LatinSquare(), Ordering(), Sorted()):
        yield check_repr, ord


def test_bizarre_inequality():
    assert (Shuffle() == 1) is False


def test_schema_string():
    assert OrderSchema.from_any('Ordering') == Ordering()


def test_schema_list():
    assert OrderSchema.from_any(['Shuffle', 2]) == Shuffle(2)


def test_schema_dict():
    spec = {
        'name': 'sorted',
        'order': 'both',
    }
    assert OrderSchema.from_any(spec) == Sorted(order='both')
