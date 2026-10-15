import asyncio
import time

from sqlalchemy import text

from app.db.session import engine


async def main() -> None:
    for attempt in (1, 2):
        start = time.perf_counter()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            print(result.scalar_one())
        print(f"attempt {attempt}: {(time.perf_counter() - start) * 1000:.0f} ms")
    await engine.dispose()


asyncio.run(main())