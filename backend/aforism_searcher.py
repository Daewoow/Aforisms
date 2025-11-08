import logging
import ydb
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from huggingface_hub import AsyncInferenceClient
import os

from backend.searcher import Searcher

logger = logging.getLogger('aforism_searcher')


class AforismSearcher(Searcher):
    def __init__(self, ydb_client):
        super().__init__(ydb_client)

        self.api_token = os.environ.get("HF_TOKEN")
        if not self.api_token:
            logger.error("HF_TOKEN не найден в переменных окружения!")
            raise ValueError("HF_TOKEN не найден в переменных окружения!")

        self.client = AsyncInferenceClient(
            provider="hf-inference",
            token=self.api_token,
            timeout=60.0
        )
        self.model_id = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    async def _get_embeddings_from_api(self, texts: list[str]):
        """
        Асинхронная функция для получения эмбеддингов через AsyncInferenceCliet.
        """
        try:
            embeddings = await self.client.feature_extraction(
                text=texts,
                model=self.model_id,
                normalize=True,
            )
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Ошибка при запросе к HF API: {e}")
            if hasattr(e, 'response') and e.response.content:
                logger.error(f"Ответ API: {e.response.content.decode()}")
            return None

    async def load_data_to_search(self):
        await self.ydb_client.connect()

        async def get_all_data(session):
            query = ("SELECT *"
                     " FROM aforisms")
            result = await session.transaction().execute(
                query,
                commit_tx=True,
                settings=ydb.BaseRequestSettings().with_timeout(10).with_operation_timeout(8)
            )
            phrases = []
            if result[0].rows:
                for row in result[0].rows:
                    phrases.append({
                        'id': row.id.decode() if isinstance(row.id, bytes) else row.id,
                        'phrase': row.phrase.decode() if isinstance(row.phrase, bytes) else row.phrase,
                        'author': row.author.decode() if isinstance(row.author, bytes) else row.author,
                        'description': row.description.decode() if isinstance(row.description,
                                                                              bytes) else row.description
                    })
            return phrases

        self.data = await self.ydb_client.pool.retry_operation(get_all_data)

        if self.data:
            texts = [p['description'] for p in self.data]
            self.vectors = await self._get_embeddings_from_api(texts)
            if self.vectors is not None:
                logger.info(f"{len(self.data)} фраз загружено и векторизовано.")
            else:
                logger.warning("Не удалось получить векторы, поиск не будет работать.")
                self.vectors = np.array([])
        else:
            logger.warning("Фраз нет")
            self.vectors = np.array([])

    async def search_similar_data(self, query_text, limit=5):
        """
        Связаны не в семантическом, а в текстовом плане
        :param query_text: запрос
        :param limit: число совпадений
        :return: слова
        """
        if self.data is None or self.vectors is None:
            await self.load_data_to_search()

        if not self.data or self.vectors.size == 0:
            return []

        query_vector_response = await self._get_embeddings_from_api([query_text])
        if query_vector_response is None:
            logger.warning("Не удалось векторизовать запрос.")
            return []
        query_vector = query_vector_response[0:1]

        similarities = cosine_similarity(query_vector, self.vectors)[0]

        results = []
        for i, phrase in enumerate(self.data):
            similarity = float(similarities[i])

            if similarity > 0.3:
                results.append({
                    'id': phrase['id'],
                    'phrase': phrase['phrase'],
                    'author': phrase['author'],
                    'description': phrase['description'],
                    'similarity_score': similarity
                })

        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]

    async def add_data(self, phrase, author, description="Неизвестная фраза"):
        await self.ydb_client.connect()
        from uuid import uuid4
        phrase_id = str(uuid4())

        async def execute_query(session):
            query = """
            UPSERT INTO aforisms (id, phrase, author, description) 
            VALUES ($id, $phrase, $author, $description) 
            """

            await session.transaction().execute(
                query,
                parameters={
                    '$id': phrase_id,
                    '$phrase': phrase,
                    '$author': author,
                    '$description': description or ''
                },
                commit_tx=True
            )
            return {
                'id': phrase_id,
                'phrase': phrase,
                'author': author,
                'description': description
            }

        result = await self.ydb_client.pool.retry_operation(execute_query)
        await self.load_data_to_search()

        return result
