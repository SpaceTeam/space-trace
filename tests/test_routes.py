import pytest


def test_empty_statistic(client):
    """Start with a blank database."""

    rv = client.get("/statistic")
    assert b"Currently in the HQ (0)" in rv.data
    assert b"<strong>0</strong> members" in rv.data
