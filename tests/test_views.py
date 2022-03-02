import pytest


def test_empty_statistic(client):
    """View statistics, logged out, with a blank database."""

    res = client.get("/statistic")
    assert res.status_code == 200
    assert b"Currently in the HQ (0)" in res.data
    assert b"<strong>0</strong> members" in res.data


def test_login_page(client):
    "View login page logged out."

    res = client.get("/login")
    assert res.status_code == 200


def test_help_page(client):
    "View help page logged out."

    res = client.get("/help")
    assert res.status_code == 200


def test_home_without_login(client):
    """
    Try to view home page without beeing logged in. This should not be allwoed
    and redirect.
    """

    res = client.get("/")
    assert res.status_code == 302


def test_admin_without_login(client):
    """
    Try to view admin page without beeing logged in. This should not be allwoed
    and redirect.
    """

    res = client.get("/admin")
    assert res.status_code == 302
