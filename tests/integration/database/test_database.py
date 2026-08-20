import pytest
from sqlalchemy import text


@pytest.mark.anyio
async def test_database_connection(db_engine):

    async with db_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))

        value = result.scalar_one()

        assert value == 1
