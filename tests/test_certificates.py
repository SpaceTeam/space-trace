from datetime import date, time, timedelta
import pytest

from space_trace.certificates import (
    assert_cert_belong_to,
    calc_vaccinated_till,
)
from space_trace.models import User


def test_calc_vaccinated_till_with_active_cert():
    """Test that calculating the expiration date is correct when fed with valid
    data"""
    data = {
        -260: {
            1: {
                "dob": "1998-02-26",
                "nam": {
                    "fn": "Musterfrau-Gößinger",
                    "fnt": "MUSTERFRAU<GOESSINGER",
                    "gn": "Gabriele",
                    "gnt": "GABRIELE",
                },
                "v": [
                    {
                        "ci": "URN:UVCI:01:AT:10807843F94AEE0EE5093FBC254BD813#B",
                        "co": "AT",
                        "dn": 2,
                        "dt": date.today().isoformat(),
                        "is": "Ministry of Health, Austria",
                        "ma": "ORG-100030215",
                        "mp": "EU/1/20/1528",
                        "sd": 2,
                        "tg": "840539006",
                        "vp": "1119349007",
                    }
                ],
                "ver": "1.2.1",
            }
        },
        1: "AT",
        4: 1624458597,
        6: 1624285797,
    }

    assert calc_vaccinated_till(data) == date.today() + timedelta(days=270)


def test_calc_vaccinated_till_with_expired_cert():
    """Test that calculating the expiration date raises an exception when fed with expired data"""
    data = {
        -260: {
            1: {
                "dob": "1998-02-26",
                "nam": {
                    "fn": "Musterfrau-Gößinger",
                    "fnt": "MUSTERFRAU<GOESSINGER",
                    "gn": "Gabriele",
                    "gnt": "GABRIELE",
                },
                "v": [
                    {
                        "ci": "URN:UVCI:01:AT:10807843F94AEE0EE5093FBC254BD813#B",
                        "co": "AT",
                        "dn": 2,
                        "dt": (date.today() - timedelta(days=365)).isoformat(),
                        "is": "Ministry of Health, Austria",
                        "ma": "ORG-100030215",
                        "mp": "EU/1/20/1528",
                        "sd": 2,
                        "tg": "840539006",
                        "vp": "1119349007",
                    }
                ],
                "ver": "1.2.1",
            }
        },
        1: "AT",
        4: 1624458597,
        6: 1624285797,
    }

    with pytest.raises(Exception):
        assert calc_vaccinated_till(data)


def test_calc_vaccinated_till_with_first_shot():
    """Test that calculating the expiration date raises an exception if that
    is not the last shot"""
    data = {
        -260: {
            1: {
                "dob": "1998-02-26",
                "nam": {
                    "fn": "Musterfrau-Gößinger",
                    "fnt": "MUSTERFRAU<GOESSINGER",
                    "gn": "Gabriele",
                    "gnt": "GABRIELE",
                },
                "v": [
                    {
                        "ci": "URN:UVCI:01:AT:10807843F94AEE0EE5093FBC254BD813#B",
                        "co": "AT",
                        "dn": 1,
                        "dt": date.today().isoformat(),
                        "is": "Ministry of Health, Austria",
                        "ma": "ORG-100030215",
                        "mp": "EU/1/20/1528",
                        "sd": 2,
                        "tg": "840539006",
                        "vp": "1119349007",
                    }
                ],
                "ver": "1.2.1",
            }
        },
        1: "AT",
        4: 1624458597,
        6: 1624285797,
    }

    with pytest.raises(Exception):
        assert calc_vaccinated_till(data)


def test_assert_cert_belong_to_with_matching():
    user = User("Tester", "ada.lovelace@spaceteam.at", "space")
    data = {
        -260: {
            1: {
                "nam": {
                    "fnt": "LOVELACE",
                    "gnt": "ADA",
                },
            },
        },
    }

    assert_cert_belong_to(data, user)


def test_assert_cert_belong_to_with_not_matching():
    user = User("Tester", "ada.lovelace@spaceteam.at", "space")
    data = {
        -260: {
            1: {
                "nam": {
                    "fnt": "MARGRET",
                    "gnt": "HAMILTON",
                },
            },
        },
    }

    with pytest.raises(Exception):
        assert assert_cert_belong_to(data, user)


def test_assert_cert_belong_to_with_matching_double_name():
    """
    Sometimes the email doesn't have all middle names but the certificates
    have.
    """
    user = User("Tester", "anna.bauer@spaceteam.at", "space")
    data = {
        -260: {
            1: {
                "nam": {
                    "fnt": "BAUER",
                    "gnt": "ANNA-MARIE",
                },
            },
        },
    }

    with pytest.raises(Exception):
        assert assert_cert_belong_to(data, user)
