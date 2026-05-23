import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter(tags=["files"])


def _safe_target(outputs_dir: str, file_path: str) -> Path | None:
    """Resolve path di bawah outputs_dir; None kalau di luar (path traversal) (§13)."""
    base = Path(outputs_dir).resolve()
    target = (base / file_path).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        return None
    return target


@router.get("/files/{file_path:path}")
async def serve_file(file_path: str) -> FileResponse:
    target = await asyncio.to_thread(_safe_target, get_settings().outputs_dir, file_path)
    if target is None:
        raise HTTPException(status_code=404, detail="file tidak ditemukan")
    return FileResponse(target)
