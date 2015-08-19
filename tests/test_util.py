from itertools import product
import pytest
from experimentator._util import as_context


@pytest.mark.parametrize(
    ('args', 'kwargs'),
    product(
        [(), (1,), (1, 'two')],
        [{}, {'a': 1}, {'a': '1', '2': []}],
    ),
)
def test_as_context(args, kwargs):
    visited = []

    def not_context(*inner_args, **inner_kwargs):
        visited.append('inside')
        return inner_args, inner_kwargs

    with as_context(not_context, *args, **kwargs) as result:
        assert visited == ['inside']
        assert result == (args, kwargs)
