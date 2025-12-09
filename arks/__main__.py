"""Entry point for the arks module.

This module provides tools for managing the ark identifier resolver configuration.

"""

import dataclasses
import datetime
import json
import logging
import os
import sys
import typing

import click
import httpx
import sqlalchemy

import rslv.lib_rslv.piddefine
from arks import __version__, APP_NAME
from arks import config as appconfig

class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles dataclasses and datetime instances."""

    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime.datetime):
            return o.isoformat(timespec="seconds")
        return super().default(o)


def logging_name_to_level(name, default=logging.INFO):
    name = name.strip().upper()
    levels = logging.getLevelNamesMapping()
    try:
        return levels[name]
    except KeyError:
        pass
    return default


def get_logger():
    return logging.getLogger(APP_NAME)


def records_to_db(
    records: typing.Dict[str, typing.Any],
    db_str: str,
    clear_existing: bool = False
) -> typing.Tuple[int, int, int, int]:
    """Mapping from an ARK NAAN record (naan) to a resolver PidDefinition (pd)

    pd.scheme = "ark"
    pd.prefix = naan.what
    pd.value = None
    pd.splitter = None
    pd.pid_model =
    pd.target = naan.target.url
    pd.http_code = naan.target.http_code
    pd.canonical = "ark:/${prefix}/${value}
    pd.properties = naan
    pd.synonym_for = None

    Shoulder records map the same, except:
    pd.prefix = naan.what before "/"
    pd.value = naan.what after "/"
    """

    L = get_logger()
    engine = sqlalchemy.create_engine(db_str, pool_pre_ping=True)
    rslv.lib_rslv.piddefine.create_database(engine, description="ark prefixes and shoulders")
    session = rslv.lib_rslv.piddefine.get_session(engine)
    repository = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    # check to see if the list of records is more recent than the repository
    meta = repository.get_metadata()
    records_modified_date = datetime.datetime.fromisoformat(records["metadata"]["date_modified"])
    _total = 0
    _added = 0
    _updated = 0
    _nsynonyms = 0
    if meta["updated"] is not None:
        if meta["updated"] > records_modified_date:
            L.info("Registry is concurrent with naan records")
            return (_total, _added, _updated, _nsynonyms)
    _synonyms = []
    # These are all arks
    _scheme = "ark"
    # Template pattern for a canonical ark representation
    # TODO: deal with the slash
    _canonical = "ark:/${prefix}/${value}"

    try:
        # Add a base ark: scheme definition.
        entry = rslv.lib_rslv.piddefine.PidDefinition(
            scheme="ark",
            target="/.info/${pid}",
            canonical=_canonical,
            synonym_for=None,
            properties={
                "what": "ark",
                "name": "Archival Resource Key",
            },
        )
        res = repository.add_or_update(entry)
        if res["n_changes"] < 0:
            L.info("Added entry %s", res["uniq"])
        elif res["n_changes"] > 0:
            L.info("Updated entry %s with %s changes", res["uniq"], res["n_changes"])
        else:
            L.info("Existing entry %s no changes.", res["uniq"])
    except Exception as e:
        L.warning(e)
        pass

    record_type_names = [
        "PublicNAAN",
        "PublicNAANShoulder",
    ]

    for record in records["data"]:
        entry = None
        if record.get("rtype") in record_type_names:
            _prefix = record.get("what")
            _value = None
            if record['rtype'] == 'PublicNAANShoulder':
                _prefix = record.get("naan", None)
                _value = record.get("shoulder", None)
            if _value is None and _prefix is None:
                L.warning("Entry %s is has null prefix and value.", record["what"])
                continue
            _target = record.get("target", {}).get("url")
            if _target is None:
                _target = f"/.info/{_scheme}/{_prefix}"
            _properties = record
            _http_code = record.get("target", {}).get("http_code", 302)
            _properties["target"] = {"DEFAULT": record.get("target")}
            entry = rslv.lib_rslv.piddefine.PidDefinition(
                scheme=_scheme,
                prefix=_prefix,
                value=_value,
                target=_target,
                http_code = _http_code,
                canonical=_canonical,
                synonym_for=None,
                properties=_properties,
            )
        _total += 1
        if entry is not None:
            try:
                res = repository.add_or_update(entry)
                uniq = res.get("uniq", entry.uniq)
                n_changes = res.get("n_changes", -1)
                if n_changes < 0:
                    _added += 1
                    L.info("Added %s", uniq)
                elif n_changes == 0:
                    L.info("No changes for %s", uniq)
                else:
                    _updated += 1
                    L.info("Updated %s with %s changes", uniq, n_changes)
            except sqlalchemy.exc.IntegrityError as e:
                repository._session.rollback()
                L.exception(e)
                L.error("Failed to add key for %s", entry.uniq)
    repository.refresh_metadata()
    return (_total, _added, _updated, _nsynonyms)


@click.group(name="cli")
@click.pass_context
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, readable=True),
    default=None,
)
def cli(ctx, config) -> int:
    msg = ""
    if config is not None:
        os.environ[appconfig.SETTINGS_FILE_KEY] = config
        msg = f"Using configuration from --config option: {config}"
    else:
        _efile = os.environ.get(appconfig.SETTINGS_FILE_KEY, None)
        if _efile is not None:
            msg = f"Using configuration from {appconfig.SETTINGS_FILE_KEY} : {_efile}"
        else:
            if os.path.exists(".env"):
                msg = "Using configuration from file: .env"
            else:
                msg = "Warning: Using default configuration."
    cfg = appconfig.get_settings(env_file=config)
    logging.basicConfig(
        filename=cfg.log_filename,
        level=logging_name_to_level(cfg.log_level),
        format=cfg.log_format
    )
    if cfg.debug_sql:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    L = logging.getLogger(APP_NAME)
    L.info(msg)
    ctx.obj = cfg
    return 0


@cli.command("info")
@click.pass_obj
def get_info(config: appconfig.Settings) -> int:
    """
    Print application version and basic status.
    """
    L = get_logger()
    engine = sqlalchemy.create_engine(config.db_connection_string, pool_pre_ping=True)
    session = rslv.lib_rslv.piddefine.get_session(engine)
    repository = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
    res = {
        "version": __version__,
        "environment": config.environment,
        "status": "not initialized",
        "description": None,
        "created": None,
        "updated": None,
        "schemes": {
            "total": 0,
            "valid": 0
        }
    }
    try:
        meta = repository.get_metadata()
        res["description"] = meta.get("description", "")
        res["created"] = meta.get("created", "")
        res["updated"] = meta.get("updated", "")
        res["status"] = "initialized"
        schemes = repository.list_schemes(valid_targets_only=False)
        _schemes = schemes.all()
        res["schemes"]["total"] = len(_schemes)
        schemes = repository.list_schemes(valid_targets_only=True)
        res["schemes"]["valid"] = len(schemes.all())
        L.debug(_schemes)
        for scheme in _schemes:
            s = scheme[0]
            L.debug("scheme = %s", s)
            prefixes = repository.list_prefixes(s).all()
            res["schemes"][s] = {"prefix_count": len(prefixes)}
    except Exception as e:
        L.error(e)
        pass
    if res["schemes"]["total"] == 0:
        L.warning("No schemes have been loaded!")
    print(json.dumps(res, indent=2, cls=EnhancedJSONEncoder))
    return 0


@cli.command("load-naans")
@click.pass_obj
@click.option(
    "-s",
    "--source",
    default=None,
    help="Source JSON NAANs file or url"
)
def load_naans(config:appconfig.Settings, source:str) -> int:
    """
    Load the identifier definitions from a NAANs json file.

    Default is specified in arks/config.py (overridden by settings)
    """
    L = get_logger()
    L.info("Loading NAAN records from %s", source)
    records = []
    if source is None:
        source = config.naans_source
    if os.path.exists(source):
        with open(source, "r") as f:
            records = json.load(f)
    else:
        records = httpx.get(source).json()
    res = records_to_db(records, config.db_connection_string)
    L.info(f"Processed {res[0]} records, added {res[1]}, updated {res[2]}, synonyms {res[3]}.")
    print("Load to db complete.")
    return 0


@cli.command("load-arks")
@click.pass_obj
@click.option(
    "-s",
    "--source",
    default=None,
    help="Specific ARK identifier records in JSON."
)
def load_arks(config:appconfig.Settings, source:str) -> int:
    """Load specific ARKs into the resolver configuration.

    This operation loads more specific ARK identifiers into the resolver
    configuration enabling this service to resolve identifiers
    in addition to the entries in the naan registry.

    This configuration should be used with caution since it
    can override resolution for existing records.

    The source records should contain at least:
      scheme
      prefix
      value
      target
      http_code

    Anny additional properties are added to the "properties" element of the record.
    """
    L = get_logger()
    records = []
    if source.lower().endswith(".jsonl"):
        # Treat as json-lines formet
        with open(source, "r") as f:
            while line := f.readline():
                records.append(json.loads(line))
    else:
        with open(source, "r") as f:
            records = json.load(f)
    L.info("Read %s records from %s", len(records), source)
    pass


try:
    import uvicorn

    @cli.command("serve")
    @click.pass_obj
    @click.option(
        "-r",
        "--reload",
        is_flag=True,
        default=False,
        help="Enable service reload on source change.",
    )
    @click.option(
        "-w",
        "--workers",
        type=int,
        default=config.workers,
        help="Number of workers to run.",
    )
    def dev_server(config:appconfig.Settings, reload:bool, workers:int) -> int:
        """Run a local development server.
        For single worker dev server with reload on code changes, use:
            arks serve --reload

        For multi-worker production-like server, use:
            arks serve --workers 4
        4 being the number of desired workers (handles about 500 TPS on my m5 mac).
        """
        uvicorn.run(
            "arks.app:app",
            host=config.devhost,
            port=config.devport,
            log_level=config.log_level,
            reload=reload,
            workers=workers,
            # There's a balance to be struck between concurrency and exhausting file handles.
            # This seems about the max for this application on a typical dev system.
            limit_concurrency=220,
        )
        return 0

except ImportError:
    print("Install uvicorn for development serve option to be available.")


def main() -> int:
    cli(prog_name="arks")
    return 0

if __name__ == "__main__":
    sys.exit(main())
