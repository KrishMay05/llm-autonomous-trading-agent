"""Tests for the circuit breaker system."""

from __future__ import annotations

from src.risk.circuit_breakers import CircuitBreaker


def test_trip_and_is_tripped():
    cb = CircuitBreaker()
    assert not cb.is_tripped()
    cb.trip("daily_loss")
    assert cb.is_tripped()
    cb.trip("error_rate")
    assert cb.is_tripped()
    cb.trip("reconcile_failed")
    assert cb.is_tripped()
    assert "daily_loss" in cb.tripped_reasons
    assert "error_rate" in cb.tripped_reasons
    assert "reconcile_failed" in cb.tripped_reasons


def test_reset():
    cb = CircuitBreaker()
    cb.trip("daily_loss")
    cb.trip("error_rate")
    cb.trip("reconcile_failed")
    assert cb.is_tripped()
    cb.reset()
    assert not cb.is_tripped()
    assert cb.tripped_reasons == []


def test_reset_daily():
    cb = CircuitBreaker()
    cb.trip("daily_loss")
    cb.trip("error_rate")
    assert cb.is_tripped()
    cb.reset_daily()
    # daily_loss cleared but error_rate still tripped
    assert not cb.daily_loss
    assert cb.error_rate
    assert cb.is_tripped()
    assert "daily_loss" not in cb.tripped_reasons
    assert "error_rate" in cb.tripped_reasons


def test_repr():
    cb = CircuitBreaker()
    cb.trip("daily_loss")
    r = repr(cb)
    assert "daily_loss=True" in r
    assert "error_rate=False" in r
