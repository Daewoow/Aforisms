import logging
import ydb
from sklearn.feature_extraction.text import TfidfVectorizer
from Levenshtein import ratio
import nltk
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

from backend.searcher import Searcher

#logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
logger = logging.getLogger('aforism_searcher')


class AforismSearcher(Searcher):
    def __init__(self, ydb_client):
        super().__init__(ydb_client)

    async def load_data_to_search(self):
        await self.ydb_client.connect()

        async def get_all_data(session):
            query = """
            SELECT *
            FROM aforisms
            """
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
                        'description': row.source.decode() if isinstance(row.description, bytes) else row.description
                    })
            return phrases

        self.data = await self.ydb_client.pool.retry_operation(get_all_data)

        if self.data:
            texts = [self.preprocess_text(p['phrase']) for p in self.data]
            self.vectorizer = TfidfVectorizer()
            self.vectors = self.vectorizer.fit_transform(texts)
            logger.info(f"{len(self.data)} фраз")
        else:
            logger.warning("Фраз нет")

    def calculate_similarity(self, query_text, phrase_text, weight_cosine: float = 0.6, weight_lev: float = 0.4):
        total_w = float(weight_cosine) + float(weight_lev)

        if total_w <= 0:
            logging.error("Сумма весов должна быть положительной")
            raise ValueError("Сумма весов должна быть положительной")

        weight_cosine /= total_w
        weight_lev /= total_w

        logging.info("Calculating similarity")

        def _normalize_for_lev(s: str) -> str:
            if not isinstance(s, str):
                s = str(s or "")
            s = s.lower()
            s = ''.join(ch for ch in s if ch.isalnum() or ch.isspace())
            s = ' '.join(s.split())
            return s

        norm_q = _normalize_for_lev(query_text)
        norm_p = _normalize_for_lev(phrase_text)
        try:
            lev_ratio = ratio(norm_q, norm_p)
        except Exception as e:
            logging.warning(f"{e}")
            lev_ratio = 0.0

        cosine_sim = 0.0
        if self.vectorizer is not None:
            try:
                phrase_vec = None
                if getattr(self, 'vectors', None) is not None and self.data:
                    idx = next((i for i, p in enumerate(self.data) if p.get('phrase') == phrase_text), None)
                    if idx is not None:
                        phrase_vec = self.vectors[idx]

                query_vec = self.vectorizer.transform([self.preprocess_text(query_text)])

                if phrase_vec is None:
                    phrase_vec = self.vectorizer.transform([self.preprocess_text(phrase_text)])

                from sklearn.metrics.pairwise import cosine_similarity
                sim = cosine_similarity(query_vec, phrase_vec)
                cosine_sim = float(sim[0, 0]) if sim.size else 0.0
                if not (0.0 <= cosine_sim <= 1.0):
                    cosine_sim = max(0.0, min(1.0, cosine_sim))
            except Exception as e:
                logging.warning(f'{e} используем только Левенштейна')
                cosine_sim = 0.0

        combined = weight_cosine * cosine_sim + weight_lev * lev_ratio
        combined = max(0.0, min(1.0, combined))
        return combined

    async def search_similar_data(self, query_text, limit=5):
        if not self.data:
            await self.load_data_to_search()

        if not self.data:
            return []

        results = []

        for phrase in self.data:
            similarity = self.calculate_similarity(query_text, phrase['phrase'])

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
            UPSERT INTO winged_phrases (id, phrase, author, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            await session.transaction().execute(
                query,
                parameters={
                    '$id': phrase_id,
                    '$phrase': phrase,
                    '$author': author,
                    'description': description or ''
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
