import logging
import ydb
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from huggingface_hub import InferenceClient
import os
from uuid import uuid4

from searcher import Searcher

logger = logging.getLogger('word_searcher')


class WordSearcher(Searcher):
    def __init__(self, ydb_client):
        super().__init__(ydb_client)

        self.api_token = os.environ.get("HF_TOKEN")
        if not self.api_token:
            logger.error("HF_TOKEN не найден в переменных окружения!")
            raise ValueError("HF_TOKEN не найден в переменных окружения!")

        self.client = InferenceClient(
            token=self.api_token,
            timeout=60.0
        )
        self.model_id = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def _get_embeddings_from_api(self, texts: list[str]):
        try:
            embeddings = self.client.feature_extraction(
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

    def load_data_to_search(self):
        self.ydb_client.connect()

        def get_all_data(session):
            query = ("SELECT * FROM words")
            result = session.transaction().execute(
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

        self.data = self.ydb_client.pool.retry_operation_sync(get_all_data)

        if self.data:
            texts = [p['description'] for p in self.data]
            self.vectors = self._get_embeddings_from_api(texts)
            if self.vectors is not None:
                logger.info(f"Загружено и векторизовано {len(self.data)} слов.")
            else:
                logger.warning("Не удалось получить векторы, поиск не будет работать.")
                self.vectors = np.array([])
        else:
            self.vectors = np.array([])
            logger.warning("Слова не найдены в БД.")

    def calculate_similarity(self, query_text, word_text):
        logger.info("Calculating similarity (semantic) for word")
        vectors_response = self._get_embeddings_from_api([query_text, word_text])
        if vectors_response is None:
            return 0.0
        vectors = vectors_response
        sim = cosine_similarity([vectors[0]], [vectors[1]])
        return float(sim[0, 0])

    def search_similar_data(self, query_text, limit=5):
        if self.data is None or self.vectors is None:
            self.load_data_to_search()

        if not self.data or self.vectors.size == 0:
            return []

        query_vector_response = self._get_embeddings_from_api([query_text])
        if query_vector_response is None:
            logger.warning("Не удалось векторизовать запрос.")
            return []

        query_vector = query_vector_response[0:1]
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

    def add_data(self, word, description="Интересное словечко"):
        self.ydb_client.connect()
        if not self.ydb_client.pool:
            print("Нет пула сессий YDB — не могу добавить данные.")
            return None

        new_id = str(uuid4())
        q_id = json.dumps(new_id)
        q_word = json.dumps(word)
        q_desc = json.dumps(description)

        def execute_query(session):
            query = (
                f"UPSERT INTO words (id, word, description) "
                f"VALUES ({q_id}, {q_word}, {q_desc})"
            )
            session.transaction().execute(
                query,
                commit_tx=True,
                settings=ydb.BaseRequestSettings().with_timeout(10).with_operation_timeout(8)
            )
            return {
                'id': new_id,
                'word': word,
                'description': description
            }

        try:
            result = self.ydb_client.pool.retry_operation_sync(execute_query)
            print(f"Добавлено слово: id={new_id}, word={word!r}")
            try:
                self.load_data_to_search()
            except Exception as e:
                print(f"Ошибка при перезагрузке данных после вставки: {e}")
            return result
        except Exception as e:
            print(f"Ошибка при добавлении слова в YDB: {e}")
            return None
