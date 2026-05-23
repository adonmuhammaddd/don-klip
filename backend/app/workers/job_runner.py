from uuid import UUID

from app.services.pipeline.pipeline import run_pipeline


async def run_job(job_id: UUID) -> None:
    """Entry point untuk FastAPI BackgroundTasks."""
    await run_pipeline(job_id)
