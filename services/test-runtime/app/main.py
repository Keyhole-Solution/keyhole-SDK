import logging

from fastapi import FastAPI

from .bridge import _MCP_RUN_TYPE, _MCP_URL, governance_mode
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
    mode = governance_mode()
    if mode == "governed":
        logger.info(
            "Keyhole Test Runtime started in GOVERNED mode. "
            "All realization requests gated by MCP governance at %s (run_type=%s).",
            _MCP_URL,
            _MCP_RUN_TYPE,
        )
    elif mode == "misconfigured":
        logger.error(
            "KEYHOLE_MCP_URL is set but KEYHOLE_MCP_TOKEN is missing. "
            "Realization requests will be REJECTED until both env vars are provided."
        )
    else:
        logger.warning(
            "Keyhole Test Runtime started in LOCAL-ONLY mode. "
            "Realization requests are NOT gated by Keyhole governance. "
            "Set KEYHOLE_MCP_URL and KEYHOLE_MCP_TOKEN for production use."
        )
