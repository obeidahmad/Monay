"""Phase 7 — the DI container resolves the stack and supports provider overrides."""

import pytest
from dependency_injector import providers

from monay.bootstrap import build_container
from monay.data.unit_of_work import SqlAlchemyUnitOfWork
from monay.domain.entities import Profile
from monay.domain.ports import Clock
from tests.fakes import FakeUnitOfWork


@pytest.fixture
def container():
    return build_container("sqlite://")


def test_clock_is_singleton_and_conforms(container):
    assert container.clock() is container.clock()
    assert isinstance(container.clock(), Clock)


def test_engine_is_singleton(container):
    assert container.engine() is container.engine()


def test_unit_of_work_is_a_fresh_factory(container):
    assert isinstance(container.unit_of_work(), SqlAlchemyUnitOfWork)
    assert container.unit_of_work() is not container.unit_of_work()


def test_resolves_uow_end_to_end(container):
    with container.unit_of_work() as uow:
        prof = uow.profiles.add(Profile(name="Me"))
        uow.commit()
    # a second UoW shares the singleton engine -> sees the committed data
    with container.unit_of_work() as uow:
        assert uow.profiles.by_name("Me").id == prof.id


def test_provider_override_with_fake(container):
    container.unit_of_work.override(providers.Factory(FakeUnitOfWork))
    uow = container.unit_of_work()
    assert isinstance(uow, FakeUnitOfWork)
    with uow:
        uow.profiles.add(Profile(name="X"))
        uow.commit()
    assert uow.committed
    container.unit_of_work.reset_override()
