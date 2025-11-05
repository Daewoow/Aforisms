from abc import ABCMeta, abstractmethod
from typing import Any


class TableHelper(metaclass=ABCMeta):
    DOCUMENT_API_URL = "https://docapi.serverless.yandexcloud.net/ru-central1/b1gs9bimn0os6rf19r65/etn3blkteuju2rriq4ic"

    @abstractmethod
    def create_table(self) -> Any:
        pass
