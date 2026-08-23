from fastapi import FastAPI

from app.api.v1.router import router
from app.domain.randomness import SecureRandomSource


def create_app() -> FastAPI:
    app = FastAPI(
        title="DivinationEngine",
        version="0.1.0",
        description=(
            "Mechanical divination and source-backed knowledge. "
            "This API does not generate interpretations."
        ),
    )
    app.state.random_source = SecureRandomSource()
    app.include_router(router)
    return app


app = create_app()
