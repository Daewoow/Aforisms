import logging
import ydb
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from backend.searcher import Searcher

logger = logging.getLogger('aforism_searcher')


class AforismSearcher(Searcher):
    def __init__(self, ydb_client):
        super().__init__(ydb_client)
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

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
            self.vectors = self.model.encode(texts, show_progress_bar=True)
            logger.info(f"{len(self.data)} фраз загружено и векторизовано.")
        else:
            logger.warning("Фраз нет")

    async def search_similar_data(self, query_text, limit=5):
        """
        Связаны не в семантическом, а в текстовом плане
        :param query_text: запрос
        :param limit: число совпадений
        :return: слова
        """
        if not self.data or self.vectors is None:
            await self.load_data_to_search()

        if not self.data:
            return []

        query_vector = self.model.encode([query_text])
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
