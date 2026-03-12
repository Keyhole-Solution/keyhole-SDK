import logging

from fastapi import FastAPI

from .bridge import _MCP_RUN_TYPE, _MCP_URL
from .contract import CONTRACT_VERSION, SURFACE_VERSION
from .mode import resolve_mode
from .routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Keyhole Test Runtime",
    description="Public test runtime for the Keyhole developer ecosystem.",
    version="0.1.0",
)

app.include_router(router)


@app.on_event("startup")
async def _log_bridge_mode() -> None:
    ms = resolve_mode()
    logger.info(
        "Keyhole Test Runtime v%s (contract=%s, surface=%s)",
        app.version,
        CONTRACT_VERSION,
        SURFACE_VERSION,
    )
    if ms.mode == "governed":
        logger.info(
            "Mode: GOVERNED — realization gated by MCP governance at %s (run_type=%s).",
            _MCP_URL,
            _MCP_RUN_TYPE,
        )
    elif ms.mode == "misconfigured":
        logger.error(
            "Mode: MISCONFIGURED — KEYHOLE_MCP_URL is set but KEYHOLE_MCP_TOKEN is missing. "
            "Realization requests will be REJECTED."
        )
    else:
        logger.warning(
            "Mode: LOCAL-ONLY — realization is NOT gated by Keyhole governance. "
            "Results are local-only and NOT auditable upstream. "
            "Set KEYHOLE_MCP_URL and KEYHOLE_MCP_TOKEN for governed mode."
        )
