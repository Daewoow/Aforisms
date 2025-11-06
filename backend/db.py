import os
import logging
from typing import Type

import ydb

from backend.aforism_searcher import AforismSearcher
from backend.searcher import Searcher
from backend.word_searcher import WordSearcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YDBClient:
    def __init__(self, searcher: Type[Searcher]) -> None:
        self.endpoint: str = os.getenv('YDB_ENDPOINT')
        self.database: str = os.getenv('YDB_DATABASE')
        self.driver = None
        self.pool = None
        self.vectorizer = None
        self.phrases = []
        self.phrase_vectors = None
        self.searcher: Searcher = searcher(self)

    async def connect(self) -> None:
        if not self.driver:
            logger.info(f"Подключение к YDB: {self.endpoint}, {self.database}")
            driver_config = ydb.DriverConfig(
                endpoint=self.endpoint,
                database=self.database,
                credentials=ydb.credentials_from_env_variables()
            )
            self.driver = ydb.Driver(driver_config)
            await self.driver.wait(timeout=25)
            self.pool = ydb.SessionPool(self.driver)
            logger.info("Соединение с YDB установлено")

    async def initialize_database(self) -> None:
        await self.connect()

        async def create_tables(session) -> None:
            create_query = """
            CREATE TABLE aforisms (
                id Utf8,
                phrase Utf8,
                author Utf8,
                description Utf8,
                PRIMARY KEY (id)
            );
            COMMIT;
            CREATE TABLE words (
                id Utf8,
                word Utf8,
                description Utf8,
                PRIMARY KEY (id)
            );
            COMMIT;
            """
            await session.execute_scheme_query(create_query)
            logger.info("Создали таблички")

        await self.pool.retry_operation(create_tables)
        await self.searcher.load_data_to_search()

    async def close(self):
        if self.pool:
            await self.pool.stop()
        if self.driver:
            self.driver.stop()
