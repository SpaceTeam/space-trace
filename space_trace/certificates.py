from datetime import date

CERT_EXPIRE_DURATION = 270


def is_cert_expired(cert):
    days_since = abs((date.today() - cert.date).days)

    return days_since > CERT_EXPIRE_DURATION
