from fastapi import FastAPI

from .routes import router

app = FastAPI(
    title="Keyhole Test Runtime",
    description="Public test runtime for the Keyhole developer ecosystem.",
    version="0.1.0",
)

app.include_router(router)
