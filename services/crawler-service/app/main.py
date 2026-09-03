import asyncio

from ips_db.session import make_engine, make_sessionmaker

from app.config import Settings
from app.worker import CrawlWorker


async def main() -> None:
    settings = Settings()
    engine = make_engine(settings.database_url)
    sessionmaker = make_sessionmaker(engine)
    worker = CrawlWorker(sessionmaker, settings)
    print("crawler-service: polling for pending crawl jobs...", flush=True)
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
