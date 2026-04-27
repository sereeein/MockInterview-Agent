import pytest

from mockinterview.agent.seed_bank import ROLES, load_seed_bank


@pytest.mark.parametrize("role", ROLES)
def test_seed_bank_loads(role):
    qs = load_seed_bank(role)
    assert isinstance(qs, list)
    assert len(qs) >= 1
    assert "text" in qs[0] and "angle" in qs[0] and "difficulty" in qs[0]


def test_seed_bank_unknown_role():
    with pytest.raises(ValueError):
        load_seed_bank("biz")
