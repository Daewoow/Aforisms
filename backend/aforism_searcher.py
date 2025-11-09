import logging
import ydb
from uuid import uuid4
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from huggingface_hub import InferenceClient 
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
            query = ("SELECT * FROM aforisms")
            result = session.transaction().execute( 
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

        self.data = self.ydb_client.pool.retry_operation_sync(get_all_data) 

        if self.data:
            texts = [p['description'] for p in self.data]
            self.vectors = self._get_embeddings_from_api(texts) 
            if self.vectors is not None:
                logger.info(f"{len(self.data)} фраз загружено и векторизовано.")
            else:
                logger.warning("Не удалось получить векторы, поиск не будет работать.")
                self.vectors = np.array([])
        else:
            logger.warning("Фраз нет")
            self.vectors = np.array([])

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

    def add_data(self, phrase, author="Народ", description="Неизвестная фраза"):
        self.ydb_client.connect()
        if "--" in phrase or "--" in author or "--" in description:
            return None

        if not self.ydb_client.pool:
            print("Нет пула сессий YDB — не могу добавить данные.")
            return None

        new_id = str(uuid4())
        q_id = json.dumps(new_id)
        q_phrase = json.dumps(phrase)
        q_author = json.dumps(author)
        q_desc = json.dumps(description)

        def execute_query(session):
            query = (
                f"UPSERT INTO aforisms (id, phrase, author, description) "
                f"VALUES ({q_id}, {q_phrase}, {q_author}, {q_desc})"
            )
            session.transaction().execute(
                query,
                commit_tx=True,
                settings=ydb.BaseRequestSettings().with_timeout(10).with_operation_timeout(8)
            )
            return {
                'id': new_id,
                'phrase': phrase,
                'author': author,
                'description': description
            }

        try:
            result = self.ydb_client.pool.retry_operation_sync(execute_query)
            print(f"Добавлена фраза: id={new_id}, phrase={phrase!r}")
            try:
                self.load_data_to_search()
            except Exception as e:
                print(f"Ошибка при перезагрузке данных после вставки: {e}")
            return result
        except Exception as e:
            print(f"Ошибка при добавлении фразы в YDB: {e}")
            return None
