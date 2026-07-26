"""Tests for the naan_records.json freshness gate in records_to_db.

The gate must compare the incoming file's metadata.date_modified against the
date_modified of the last file actually loaded (content vs content), not
against the wall-clock time the last load completed. The registry stamps
date_modified before the file is published to gh-pages (build + CDN latency),
so a load that runs inside that window would otherwise mask the newer file
forever.
"""
import datetime

import pytest
import sqlalchemy

import rslv.lib_rslv.piddefine as piddefine
from arks.__main__ import records_to_db

UTC = datetime.timezone.utc


def public_naan(what: str, url: str) -> dict:
    return {
        "rtype": "PublicNAAN",
        "what": what,
        "where": url,
        "target": {"url": url + "/ark:/${content}", "http_code": 302},
        "when": "2020-01-01T00:00:00+00:00",
        "who": {"name": "Test Org", "acronym": "TO"},
        "na_policy": {"orgtype": "NP", "policy": "NR", "tenure": "2020"},
    }


def records_file(date_modified: datetime.datetime, naans: list) -> dict:
    return {
        "metadata": {
            "version": "2.0",
            "date_created": "2024-08-26T08:09:51+00:00",
            "date_modified": date_modified.isoformat(timespec="seconds"),
            "description": "NAAN repository",
        },
        "data": naans,
        "index": [[n["what"], i] for i, n in enumerate(naans)],
    }


@pytest.fixture
def db_str(tmp_path):
    return f"sqlite:///{tmp_path}/registry.sqlite"


def get_target(db_str: str, what: str):
    engine = sqlalchemy.create_engine(db_str)
    session = piddefine.get_session(engine)
    try:
        entry = piddefine.PidDefinitionCatalog(session).get(scheme="ark", prefix=what)
        return None if entry is None else entry.target
    finally:
        session.close()
        engine.dispose()


def test_file_with_newer_content_loads_even_if_stamped_before_last_load(db_str):
    """An update stamped during the publish/CDN latency window must not be skipped.

    Timeline: v1 (stamp T-100s) is loaded "now"; v2 contains an update to the
    same NAAN and is stamped T-50s -- newer content than anything loaded, but
    older than the load's completion time. v2 only became fetchable after the
    v1 load because of the gh-pages build + CDN cache delay.
    """
    now = datetime.datetime.now(tz=UTC)
    v1 = records_file(
        now - datetime.timedelta(seconds=100),
        [public_naan("99901", "http://old.example.org")],
    )
    records_to_db(v1, db_str)
    assert get_target(db_str, "99901") == "http://old.example.org/ark:/${content}"

    v2 = records_file(
        now - datetime.timedelta(seconds=50),
        [public_naan("99901", "https://new.example.org")],
    )
    total, added, updated, _ = records_to_db(v2, db_str)

    assert updated == 1, "newer-content file was skipped by the freshness gate"
    assert get_target(db_str, "99901") == "https://new.example.org/ark:/${content}"


def test_reloading_same_file_version_is_skipped(db_str):
    """The gate must still short-circuit when the same file version is re-fetched."""
    stamp = datetime.datetime.now(tz=UTC) - datetime.timedelta(seconds=100)
    v1 = records_file(stamp, [public_naan("99901", "http://old.example.org")])
    records_to_db(v1, db_str)

    total, added, updated, _ = records_to_db(v1, db_str)

    assert (total, added, updated) == (0, 0, 0)
