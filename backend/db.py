import os
import logging
import ydb

from backend.aforism_searcher import AforismSearcher
from backend.word_searcher import WordSearcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YDBClient:
    def __init__(self):
        self.endpoint: str = os.getenv('YDB_ENDPOINT')
        self.database: str = os.getenv('YDB_DATABASE')
        self.driver = None
        self.pool = None

        self.aforism_searcher = AforismSearcher(self)
        self.word_searcher = WordSearcher(self)

    async def connect(self) -> None:
        if not self.driver:
            logger.info(f"Подключение к YDB: {self.endpoint}, {self.database}")
            driver_config = ydb.DriverConfig(
                endpoint=self.endpoint,
                database=self.database,
                credentials=ydb.credentials_from_env_variables()
            )
            try:
                self.driver = ydb.Driver(driver_config)
                await self.driver.wait(timeout=30, fail_fast=True)
                self.pool = ydb.SessionPool(self.driver, size=10)
                logger.info("Соединение с YDB установлено")
            except Exception as e:
                logger.error(f"Не удалось подключиться к YDB: {e}", exc_info=True)
                self.driver = None

    async def initialize_database(self) -> None:
        await self.connect()
        if not self.pool:
            logger.error("Инициализация БД невозможна, нет пула сессий.")
            return

        async def create_tables(session) -> None:
            try:
                await session.execute_scheme_query("""
                    CREATE TABLE aforisms (
                        id Utf8,
                        phrase Utf8,
                        author Utf8,
                        description Utf8,
                        PRIMARY KEY (id)
                    )
                """)
                logger.info("Таблица 'aforisms' создана.")
            except ydb.SchemeError:
                logger.info("Таблица 'aforisms' уже существует.")

            try:
                await session.execute_scheme_query("""
                    CREATE TABLE words (
                        id Utf8,
                        word Utf8,
                        description Utf8,
                        PRIMARY KEY (id)
                    )
                """)
                logger.info("Таблица 'words' создана.")
            except ydb.SchemeError:
                logger.info("Таблица 'words' уже существует.")

        try:
            await self.pool.retry_operation(create_tables)
            logger.info("Проверка таблиц завершена.")
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}", exc_info=True)

        try:
            await self.aforism_searcher.load_data_to_search()
        except Exception as e:
            logger.error(f"Ошибка при загрузке афоризмов: {e}", exc_info=True)

        try:
            await self.word_searcher.load_data_to_search()
        except Exception as e:
            logger.error(f"Ошибка при загрузке слов: {e}", exc_info=True)

    async def close(self):
        if self.pool:
            await self.pool.stop()
        if self.driver:
            self.driver.stop()


ydb_client = YDBClient()
