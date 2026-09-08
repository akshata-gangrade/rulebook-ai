from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ask import router as ask_router
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title="Rulebook AI",
    description="Evidence-grounded university rulebook QA system.",
    version="1.0.0",
)


# Allow the React frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """
    Basic health check for the API.
    """
    return {
        "status": "ok",
        "service": "rulebook-ai",
    }


app.include_router(ask_router)