import logging
import ydb
import nltk
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ... (проверки nltk можно оставить) ...

from backend.searcher import Searcher

logger = logging.getLogger('aforism_searcher')


class AforismSearcher(Searcher):
    def __init__(self, ydb_client):
        super().__init__(ydb_client)  # В 'searcher.py' можно убрать 'preprocess_text'
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        # self.vectors - это теперь будет numpy массив с эмбеддингами
        # self.data - остается как есть

    # ВАЖНО: 'preprocess_text' из 'searcher.py' нужно УБРАТЬ или НЕ ИСПОЛЬЗОВАТЬ.
    # Трансформерам нужны "сырые" предложения, без лемматизации и удаления стоп-слов.

    # Этот метод больше не нужен, т.к. 'preprocess_text' не используется
    # def preprocess_text(self, text): ...

    async def load_data_to_search(self):
        await self.ydb_client.connect()

        async def get_all_data(session):
            query = "SELECT id, phrase, author, description FROM aforisms"
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
                        # Убедитесь, что 'description' правильно мапится,
                        # в коде aforism_searcher.py у вас было 'row.source', а в db.py 'description'
                    })
            return phrases

        self.data = await self.ydb_client.pool.retry_operation(get_all_data)

        if self.data:
            # Получаем "сырые" тексты фраз
            texts = [p['phrase'] for p in self.data]

            # Кодируем их в векторы (эмбеддинги)
            # Это может занять время, если фраз много
            self.vectors = self.model.encode(texts, show_progress_bar=True)
            logger.info(f"{len(self.data)} фраз загружено и векторизовано.")
        else:
            logger.warning("Фраз нет")

    # Этот метод можно удалить, т.к. 'calculate_similarity' больше не будет
    # вызываться в цикле. Мы будем считать все сразу.
    # def calculate_similarity(...): ...

    async def search_similar_data(self, query_text, limit=5):
        if not self.data or self.vectors is None:
            await self.load_data_to_search()

        if not self.data:
            return []

        # 1. Векторизуем поисковый запрос
        query_vector = self.model.encode([query_text])

        # 2. Считаем косинусную близость между вектором запроса
        #    и ВСЕМИ векторами фраз в нашей базе
        #    Это ОЧЕНЬ быстрая операция с numpy
        similarities = cosine_similarity(query_vector, self.vectors)[0]

        # 3. Собираем результаты
        results = []
        for i, phrase in enumerate(self.data):
            similarity = float(similarities[i])

            if similarity > 0.3:  # Порог можно будет подстроить
                results.append({
                    'id': phrase['id'],
                    'phrase': phrase['phrase'],
                    'author': phrase['author'],
                    'description': phrase['description'],
                    'similarity_score': similarity
                })

        # 4. Сортируем и возвращаем топ-N
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
            """  # Используем $id, $phrase и т.д. для именованных параметров YDB

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

        # ВАЖНО: После добавления новой фразы нужно
        # ПЕРЕСЧИТАТЬ все векторы
        await self.load_data_to_search()

        return result
