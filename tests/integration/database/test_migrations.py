import subprocess

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_alembic_upgrade(db_engine):
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    async with db_engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
            )
        )

        tables = result.scalars().all()

    assert "users" in tables
    assert "alembic_version" in tables
