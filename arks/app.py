import contextlib
import functools
import logging
import typing

import fastapi
import fastapi.middleware.cors
import fastapi.staticfiles
import fastapi.templating
import sqlalchemy.orm
import rslv.routers.resolver

from arks.config import get_settings
from arks import __version__, APP_NAME


def get_logger():
    return logging.getLogger(APP_NAME)


def setup_logger(app: fastapi.FastAPI) -> None:
    _levels = {
        "DEBUG": logging.DEBUG,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "CRITICAL": logging.CRITICAL
    }
    level_str = app.state.settings.log_level.upper()
    logging.basicConfig(level=_levels[level_str])


@functools.lru_cache(maxsize=32)
def get_engine(dbcnstr: str, pool_size:int=50, pool_recycle:int=300) -> sqlalchemy.engine.base.Engine:
    engine =  sqlalchemy.create_engine(
        dbcnstr,
        pool_size=pool_size,
        pool_recycle=pool_recycle,
    )
    return engine


@contextlib.contextmanager
def get_dbsession(dbengine) -> typing.Iterator[sqlalchemy.orm.Session]:
    dbsession = sqlalchemy.orm.sessionmaker(bind=dbengine)()
    try:
        yield dbsession
    except Exception:
        dbsession.rollback()
        raise
    finally:
        dbsession.close()


async def app_report_startup(app: fastapi.FastAPI) -> None:
    L = get_logger()
    L.info("Application settings")
    L.info("environment = %s", app.state.settings.environment )
    L.info("db_connection_string = %s", app.state.settings.db_connection_string)
    L.info("allow_appinfo = %s", app.state.settings.allow_appinfo)
    L.info("service_pattern = %s", app.state.settings.service_pattern)
    L.info("auto_introspection = %s", app.state.settings.auto_introspection)


@contextlib.asynccontextmanager
async def dbengine_lifespan(app: fastapi):
    await app_report_startup(app)
    dbcnstr = app.state.settings.db_connection_string
    app.state.dbengine = get_engine(dbcnstr)
    yield
    if app.state.dbengine is not None:
        app.state.dbengine.dispose()


app = fastapi.FastAPI(
    title="ARKS",
    description=__doc__,
    version=__version__,
    contact={"name": "Dave Vieglais", "url": "https://github.com/arksorg/arksorg-site"},
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/mit/",
    },
    lifespan=dbengine_lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api",
)

app.state.settings = get_settings()
setup_logger(app)

# Enables CORS for UIs on different domains
app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=["*", ],
    allow_credentials=True,
    allow_methods=["*", ],
    allow_headers=["*", ],
)

def get_relative_url_for(name: str, *args: typing.Any, **kwargs: typing.Any) -> str:
    _path = kwargs.get("path", "/")
    return app.url_path_for(name, path=_path)


@app.middleware("http")
async def add_db_session_middleware(request: fastapi.Request, call_next):
    with get_dbsession(request.app.state.dbengine) as dbsession:
        request.state.dbsession = dbsession
        response = await call_next(request)
        return response



app.mount(
    "/static",
    fastapi.staticfiles.StaticFiles(directory=app.state.settings.static_dir),
    name="static",
)


templates = fastapi.templating.Jinja2Templates(
    directory=app.state.settings.template_dir
)

templates.env.globals.setdefault("relurl_for", get_relative_url_for)


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    raise fastapi.HTTPException(status_code=404, detail="Not found")


@app.get("/", include_in_schema=False)
async def redirect_docs(request: fastapi.Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "environment": app.state.settings.environment,
            "version": __version__,
        },
    )


@app.get("/_{page:path}", include_in_schema=False)
async def human_pages(request: fastapi.Request, page: str):
    L = get_logger()
    try:
        return templates.TemplateResponse(
            page,
            {
                "request": request,
                "environment": app.state.settings.environment,
                "version": __version__,
            },
        )
    except Exception as e:
        L.exception(e)
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "environment": app.state.settings.environment,
            "version": __version__,
        },
        status_code=404,
    )


if app.state.settings.allow_appinfo:
    @app.get("/.appinfo")
    async def app_info(request: fastapi.Request):
        return app.state.settings


app.include_router(
    rslv.routers.resolver.router,
)
