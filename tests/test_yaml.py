import numpy as np
import pytest

from experimentator import yaml
from tests.test_design import make_heterogeneous_tree


@pytest.mark.parametrize('data', [
    np.random.randn(5),
    1+1j,
    np.array([1, 1+1j, 1j]),
    np.arange(200, 220),
    make_heterogeneous_tree(),
])
def test_round_trip(data):
    cmp = yaml.load(yaml.dump(data)) == data
    if isinstance(cmp, np.ndarray):
        assert np.all(cmp)
    else:
        assert cmp
