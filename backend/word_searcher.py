import logging
import ydb
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from uuid import uuid4

from backend.searcher import Searcher

logger = logging.getLogger('word_searcher')


class WordSearcher(Searcher):
    def __init__(self, ydb_client):
        super().__init__(ydb_client)
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("Модель SentenceTransformer загружена для WordSearcher.")

    async def load_data_to_search(self):
        await self.ydb_client.connect()

        async def get_all_data(session):
            query = ("SELECT * "
                     "FROM words")
            result = await session.transaction().execute(
                query,
                commit_tx=True,
                settings=ydb.BaseRequestSettings().with_timeout(10).with_operation_timeout(8)
            )
            words = []
            if result[0].rows:
                for row in result[0].rows:
                    words.append({
                        'id': row.id.decode() if isinstance(row.id, bytes) else row.id,
                        'word': row.word.decode() if isinstance(row.word, bytes) else row.word,
                        'description': row.description.decode() if isinstance(row.description, bytes)
                        else row.description
                    })
            return words

        self.data = await self.ydb_client.pool.retry_operation(get_all_data)

        if self.data:
            texts = [p['description'] for p in self.data]
            self.vectors = self.model.encode(texts, show_progress_bar=False)
            logger.info(f"Загружено и векторизовано {len(self.data)} слов.")
        else:
            self.vectors = np.array([])
            logger.warning("Слова не найдены в БД.")

    def calculate_similarity(self, query_text, word_text, **kwargs):
        logger.info("Calculating similarity (semantic) for word")
        vectors = self.model.encode([query_text, word_text])
        sim = cosine_similarity([vectors[0]], [vectors[1]])
        return float(sim[0, 0])

    async def search_similar_data(self, query_text, limit=5):
        if self.data is None or self.vectors is None:
            await self.load_data_to_search()

        if not self.data or self.vectors.size == 0:
            return []

        query_vector = self.model.encode([query_text])
        similarities = cosine_similarity(query_vector, self.vectors)[0]

        results = []
        for i, word_data in enumerate(self.data):
            similarity = float(similarities[i])
            if similarity > 0.4:
                results.append({
                    'id': word_data['id'],
                    'word': word_data['word'],
                    'description': word_data['description'],
                    'similarity_score': similarity
                })

        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]

    async def add_data(self, word, description=""):
        await self.ydb_client.connect()
        word_id = str(uuid4())

        async def execute_query(session):
            query = """
            UPSERT INTO words (id, word, description)
            VALUES ($id, $word, $description)
            """
            await session.transaction().execute(
                query,
                parameters={
                    '$id': word_id,
                    '$word': word,
                    '$description': description or ''
                },
                commit_tx=True
            )
            return {
                'id': word_id,
                'word': word,
                'description': description
            }

        result = await self.ydb_client.pool.retry_operation(execute_query)
        await self.load_data_to_search()
        return result
