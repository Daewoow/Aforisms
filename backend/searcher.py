from abc import ABC, abstractmethod


class Searcher(ABC):
    def __init__(self, ydb_client):
        self.vectors = None
        self.model = None
        self.data = None
        self.ydb_client = ydb_client

    @abstractmethod
    def load_data_to_search(self):
        """
        Загружает данные из БД и создает векторные эмбеддинги
        """
        pass

    @abstractmethod
    def search_similar_data(self, query_text: str, limit: int):
        """
        Ищет похожие данные, используя векторы
        """
        pass

    @abstractmethod
    def add_data(self, **kwargs):
        """
        Добавляет новые данные в БД
        """
        pass
