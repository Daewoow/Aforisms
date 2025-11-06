from abc import ABC, abstractmethod

from nltk import SnowballStemmer
from nltk.corpus import stopwords


class Searcher(ABC):
    def __init__(self, ydb_client):
        self.vectors = None
        self.vectorizer = None
        self.data = None
        self.stop_words = set(stopwords.words('russian'))
        self.stemmer = SnowballStemmer('russian')
        self.ydb_client = ydb_client

    # def preprocess_text(self, text):
    #     text = text.lower()
    #     text = ''.join([c for c in text if c.isalnum() or c.isspace()])
    #     tokens = nltk.word_tokenize(text)
    #     tokens = [self.stemmer.stem(token) for token in tokens if token not in self.stop_words and len(token) > 2]
    #     return ' '.join(tokens)

    @abstractmethod
    def calculate_similarity(self, query_text, phrase_text, weight_cosine: float, weight_lev: float):
        pass

    @abstractmethod
    async def load_data_to_search(self):
        pass

    @abstractmethod
    async def search_similar_data(self, query_text, limit: int):
        pass

    @abstractmethod
    async def add_data(self, data: str, description: str, author: str | None):
        pass


