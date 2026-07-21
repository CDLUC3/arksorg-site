"""Test cases for ARKS.

"""

import logging
import os

import fastapi.testclient
import json
import pytest
import sqlalchemy

import arks.__main__ as arksmain
from arks import config as appconfig

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
CONFIG_DB = os.path.join(THIS_FOLDER, "test.db")
ARKS_DB_CONNECTION_STRING = f"sqlite:///{CONFIG_DB}"
ARKS_NAANS_SOURCE = os.path.abspath(os.path.join(THIS_FOLDER, "test_data", "naan_records.json"))

L = logging.getLogger("__name__")

@pytest.fixture(scope="module")
def arksapp():
    # The app instance is a global in arks.app, so need to configure
    # the environment before loading the module to ensure the correct
    # settings are being used.

    os.environ["ARKS_DB_CONNECTION_STRING"] = ARKS_DB_CONNECTION_STRING
    os.environ["ARKS_NAANS_SOURCE"] = ARKS_NAANS_SOURCE

    # Now import the app
    import arks.app

    # And configure the database engine
    config = appconfig.get_settings()
    engine = sqlalchemy.create_engine(config.db_connection_string, pool_pre_ping=True, echo=False)
    arks.app.app.state.dbengine = engine

    # Load the naan records for further tests
    L.info("Loading resolver database using %s", config.db_connection_string)
    with open(config.naans_source, "r") as f:
        records = json.load(f)

    _ = arksmain.records_to_db(records, config.db_connection_string)

    # Yield the app for use in the scope of this module's tests
    yield arks.app.app
    # cleanup, remove the config db
    os.unlink(CONFIG_DB)

"""Test cases for CORS support by the web application.

Liberal CORS support is needed to enable in-browser programmatic use of
PID identified resources.
Disable cors tests for now.
"""
def x_test_cors_headers(arksapp):
    client = fastapi.testclient.TestClient(arksapp, follow_redirects=False)
    headers = {
        "origin":"https://example.com/",
    }
    response = client.request("GET", "/", headers=headers)
    assert response.headers.get("access-control-allow-origin", None) == "*"
    # No origin in request -> no CORS
    response = client.request("GET", "/")
    assert response.headers.get("access-control-allow-origin", None) is None

"""Test cases for ARK resolution.
Sample records are taken from "Testing an ARK resolver instance"
https://github.com/CDLUC3/arksorg-site/blob/main/doc_src/operation_test.md

ark:/99166/w6sr6tn8:
ark:/65665/3f9748e2c-affd-44ee-9c14-4eb966e2955c: 
ark:27023/829db79be004882891dd7b88c2ea6236: 
ark:67531/metadc3211:
ark:69774/rgm2020: NLID substitution
ark:19156/tkt42/03n01: suffix passthrough
"""

info_cases = (
    ("ark:/99166/w6sr6tn8", {"uniq": "ark:99166/w6", "target": "http://socialarchive.iath.virginia.edu/ark:/${content}", "http_code": 303}),
    ("ark:/65665/3f9748e2c-affd-44ee-9c14-4eb966e2955c", {"uniq": "ark:65665", "target": "https://ezid.cdlib.org/ark:/${content}", "http_code": 302}),
    ("ark:27023/829db79be004882891dd7b88c2ea6236", {"uniq": "ark:27023", "target": "https://id.colonialcollections.nl/ark:/${content}", "http_code": 302}),
    ("ark:67531/metadc3211", {"uniq": "ark:67531", "target": "http://digital.library.unt.edu/ark:/${content}", "http_code": 302}),
    ("ark:69774/rgm2020", {"uniq": "ark:69774", "target": "https://hdlab.space/ark/${value}", "http_code": 302}),
    ("ark:19156/tkt42/03n01", {"uniq": "ark:19156/tkt42", "target": "https://vocab.participatory-archives.ch/vocab.participatory-archives.ch/brunner${suffix}", "http_code": 302}),
)

resolve_cases = (
    ("ark:/99166/w6sr6tn8", {"location":"http://socialarchive.iath.virginia.edu/ark:/99166/w6sr6tn8", "status": 303}),
    ("ark:/65665/3f9748e2c-affd-44ee-9c14-4eb966e2955c", {"location":"https://ezid.cdlib.org/ark:/65665/3f9748e2caffd44ee9c144eb966e2955c", "status": 302}),
    ("ark:27023/829db79be004882891dd7b88c2ea6236", {"location":"https://id.colonialcollections.nl/ark:/27023/829db79be004882891dd7b88c2ea6236", "status": 302}),
    ("ark:67531/metadc3211", {"location":"http://digital.library.unt.edu/ark:/67531/metadc3211", "status": 302}),
    ("ark:69774/rgm2020", {"location":"https://hdlab.space/ark/rgm2020", "status": 302}),
    ("ark:19156/tkt42/03n01", {"location":"https://vocab.participatory-archives.ch/vocab.participatory-archives.ch/brunner/03n01", "status": 302}),
)

@pytest.mark.parametrize("test,expected", info_cases)
def test_info_schemes(arksapp, test, expected):
    client = fastapi.testclient.TestClient(arksapp, follow_redirects=False)
    response = client.get(f"/.info/{test}")
    _match = response.json()
    L.info(json.dumps(_match, indent=2))
    assert _match.get("definition",{}).get("uniq",None) == expected["uniq"]
    assert _match.get("definition", {}).get("target", None) == expected["target"]
    assert _match.get("definition", {}).get("http_code", None) == expected["http_code"]
    assert response.status_code == 200

@pytest.mark.parametrize("test,expected", resolve_cases)
def test_resolve_schemes1(arksapp, test, expected):
    L.info("test_resolve_schemes1: %s", test)
    client = fastapi.testclient.TestClient(arksapp, follow_redirects=False)
    response = client.get(f"/{test}")
    _match = response.json()
    L.info(json.dumps(_match, indent=2))
    assert response.status_code == expected["status"]
    assert response.headers.get("location") == expected["location"]


