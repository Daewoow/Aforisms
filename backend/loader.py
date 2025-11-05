from abc import ABCMeta, abstractmethod


class Loader(metaclass=ABCMeta):
    DOCUMENT_API_URL = "https://docapi.serverless.yandexcloud.net/ru-central1/b1gs9bimn0os6rf19r65/etn3blkteuju2rriq4ic"

    @abstractmethod
    def load_data(self, data) -> None:
        pass
