import pytest

from truss_model import TrussBridge

L = 20.0
H = 3.0
N_VALUES = [2, 4, 6, 8, 10]


def expected_counts(truss_type, n):
    if truss_type == "warren":
        return 2 * n + 1, 4 * n - 1
    return 2 * n, 4 * n - 3


@pytest.mark.parametrize("n", N_VALUES)
@pytest.mark.parametrize("truss_type", ["pratt", "howe", "warren"])
def test_counts(truss_type, n):
    bridge = TrussBridge(truss_type, L, H, n)
    j, m = expected_counts(truss_type, n)

    assert bridge.num_nodes == j
    assert bridge.coords.shape == (j, 2)
    assert bridge.num_elements == m
    assert bridge.elements.shape == (m, 2)
    assert bridge.edof.shape == (m, 4)
    assert len(bridge.member_groups) == m
    assert len(bridge.section_classes) == m
    assert bridge.num_reactions == 3
    assert len(bridge.bc_dofs) == 3


@pytest.mark.parametrize("n", N_VALUES)
@pytest.mark.parametrize("truss_type", ["pratt", "howe", "warren"])
def test_statical_determinacy(truss_type, n):
    bridge = TrussBridge(truss_type, L, H, n)
    assert bridge.num_elements + bridge.num_reactions == 2 * bridge.num_nodes
