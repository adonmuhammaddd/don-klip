from collections.abc import AsyncIterator

import pytest

from app.db.session import engine


@pytest.fixture(autouse=True)
async def _dispose_engine() -> AsyncIterator[None]:
    """Buang connection pool setelah tiap test.

    pytest-asyncio memberi event loop baru per test; tanpa dispose, koneksi
    pooled dari loop sebelumnya dipakai lagi → 'Event loop is closed'.
    """
    yield
    await engine.dispose()
