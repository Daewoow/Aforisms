import os
import logging
import ydb
import ydb.iam

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

    def connect(self) -> None:
        if not self.driver:
            logger.info(f"Подключение к YDB: {self.endpoint}, {self.database}")
            creds = ydb.iam.MetadataUrlCredentials()

            print(f"Creds: {creds}")
            driver_config = ydb.DriverConfig(
                endpoint=self.endpoint,
                database=self.database,
                credentials=creds
            )
            try:
                self.driver = ydb.Driver(driver_config)
                print(f"Driver: {self.driver}")
                self.driver.wait(timeout=30, fail_fast=True)
                print("Дождались")
                self.pool = ydb.SessionPool(self.driver, size=10)
                print(f"Pool: {self.pool}")
                logger.info("Соединение с YDB установлено")
            except Exception as e:
                logger.error(f"Не удалось подключиться к YDB: {e}", exc_info=True)
                if self.driver:
                    self.driver.stop()
                self.driver = None

    def initialize_database(self) -> None:
        self.connect()
        if not self.pool:
            logger.error("Инициализация БД невозможна, нет пула сессий.")
            return

        def create_tables(session) -> None:
            try:
                session.execute_scheme_query("""...""")
                logger.info("Таблица 'aforisms' создана.")
            except ydb.SchemeError:
                logger.info("Таблица 'aforisms' уже существует.")

            try:
                session.execute_scheme_query("""...""")
                logger.info("Таблица 'words' создана.")
            except ydb.SchemeError:
                logger.info("Таблица 'words' уже существует.")

        try:
            self.pool.retry_operation_sync(create_tables)
            logger.info("Проверка таблиц завершена.")
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}", exc_info=True)

        try:
            self.aforism_searcher.load_data_to_search()
        except Exception as e:
            logger.error(f"Ошибка при загрузке афоризмов: {e}", exc_info=True)

        try:
            self.word_searcher.load_data_to_search()
        except Exception as e:
            logger.error(f"Ошибка при загрузке слов: {e}", exc_info=True)

    def close(self):
        if self.pool:
            self.pool.stop()
        if self.driver:
            self.driver.stop()


ydb_client = YDBClient()
