import numpy as np
from collections import Counter
import logging
import difflib

from sklearn.feature_extraction.text import TfidfVectorizer

from Levenshtein import ratio

#logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class PhraseSearcher:
    def __init__(self):
        self.phrases = None
        self.tfidf_matrix = None
        self.word_to_idx = None
        self.idf = None
        self.vectorizer = None
        self.phrase_vectors = None
        self.stop_words = {'и', 'в', 'на', 'не', 'а', 'с', 'по', 'как', 'то', 'что', 'это', 'от', 'до', 'из', 'за', 'у',
                           'о', 'к', 'для', 'но', 'или', 'да', 'ни', 'же', 'бы', 'ли', 'уж'}

    def load_phrases_for_search(self):
        self.phrases = [
            {'id': '1', 'phrase': 'Один в поле не воин', 'author': 'Unknown', 'description': ''},
            {'id': '2', 'phrase': 'Божий одуванчик', 'author': 'Unknown', 'description': ''},
            {'id': '3', 'phrase': 'Дубина стоеросовая', 'author': 'Unknown', 'description': ''},
            {'id': '4', 'phrase': 'Закадычный друг', 'author': 'Unknown', 'description': ''},
            {'id': '5', 'phrase': 'Заячья душа', 'author': 'Unknown', 'description': ''},
            {'id': '6', 'phrase': 'Казанская сирота', 'author': 'Unknown', 'description': ''},
            {'id': '7', 'phrase': 'Как буриданов осел', 'author': 'Unknown', 'description': ''},
            {'id': '8', 'phrase': 'Калиф на час', 'author': 'Unknown', 'description': ''},
            {'id': '9', 'phrase': 'Козел отпущения', 'author': 'Unknown', 'description': ''},
            {'id': '10', 'phrase': 'Мастер на все руки', 'author': 'Unknown', 'description': ''},
            {'id': '11', 'phrase': 'Мокрая курица', 'author': 'Unknown', 'description': ''},
            {'id': '12', 'phrase': 'Мухи не обидит', 'author': 'Unknown', 'description': ''},
            {'id': '13', 'phrase': 'Не пришей кобыле хвост', 'author': 'Unknown', 'description': ''},
            {'id': '14', 'phrase': 'Профессор кислых щей', 'author': 'Unknown', 'description': ''},
            {'id': '15', 'phrase': 'Рабочая лошадка', 'author': 'Unknown', 'description': ''},
            {'id': '16', 'phrase': 'Семи пядей во лбу', 'author': 'Unknown', 'description': ''},
            {'id': '17', 'phrase': 'Серая мышь', 'author': 'Unknown', 'description': ''},
            {'id': '18', 'phrase': 'Стреляный воробей', 'author': 'Unknown', 'description': ''},
            {'id': '19', 'phrase': 'Темная лошадка', 'author': 'Unknown', 'description': ''},
            {'id': '20', 'phrase': 'Шут гороховый', 'author': 'Unknown', 'description': ''},
            {'id': '21', 'phrase': 'Язык без костей', 'author': 'Unknown', 'description': ''},
            {'id': '22', 'phrase': 'Белый свет не мил', 'author': 'Unknown', 'description': ''},
            {'id': '23', 'phrase': 'Вопрос жизни и смерти', 'author': 'Unknown', 'description': ''},
            {'id': '24', 'phrase': 'Всем смертям назло', 'author': 'Unknown', 'description': ''},
            {'id': '25', 'phrase': 'Глас вопиющего в пустыне', 'author': 'Unknown', 'description': ''},
            {'id': '26', 'phrase': 'Да ни в жизнь', 'author': 'Unknown', 'description': ''},
            {'id': '27', 'phrase': 'Дойти до ручки', 'author': 'Unknown', 'description': ''},
            {'id': '28', 'phrase': 'Дорога жизни', 'author': 'Unknown', 'description': ''},
            {'id': '29', 'phrase': 'Живем один раз', 'author': 'Unknown', 'description': ''},
            {'id': '30', 'phrase': 'Жизнь берет свое', 'author': 'Unknown', 'description': ''},
            {'id': '31', 'phrase': 'Негра пенить', 'author': 'Unknown', 'description': ''},
            {'id': '32', 'phrase': 'Цыплят по осени считают', 'author': 'Unknown', 'description': ''},
            {'id': '33', 'phrase': 'О малозначительном событии, которое выдают за большое достижение',
             'author': 'Unknown', 'description': ''}
        ]

        if self.phrases:
            texts = [self.preprocess_text(p['phrase']) for p in self.phrases]
            N = len(texts)
            all_words = list(set(word for text in texts for word in text.split()))
            self.word_to_idx = {w: i for i, w in enumerate(all_words)}
            V = len(all_words)
            tf_matrix = np.zeros((N, V))
            df = np.zeros(V)
            for i, text in enumerate(texts):
                words = text.split()
                if not words:
                    continue
                counter = Counter(words)
                total = len(words)
                for word, freq in counter.items():
                    idx = self.word_to_idx[word]
                    tf_matrix[i, idx] = freq / total
                    df[idx] += 1
            self.idf = np.log(N / (df + 1)) 
            self.tfidf_matrix = tf_matrix * self.idf
            logger.info(f"Loaded {len(self.phrases)} phrases for search")
        else:
            logger.warning("No phrases found")

    def preprocess_text(self, text):
        """Предобработка текста для поиска (без NLTK)"""
        text = text.lower()
        text = ''.join([c for c in text if c.isalnum() or c.isspace()])
        tokens = text.split()
        tokens = [token for token in tokens if token not in self.stop_words and len(token) > 2]
        return ' '.join(tokens)

    def calculate_similarity(self, query_text, phrase_text, weight_cosine: float = 0.8, weight_lev: float = 0.2):
        texts = [self.preprocess_text(p['phrase']) for p in self.phrases]
        self.vectorizer = TfidfVectorizer()
        self.phrase_vectors = self.vectorizer.fit_transform(texts)
        logger.info(f"{len(self.phrases)} фраз")

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
                if getattr(self, 'phrase_vectors', None) is not None and self.phrases:
                    idx = next((i for i, p in enumerate(self.phrases) if p.get('phrase') == phrase_text), None)
                    if idx is not None:
                        phrase_vec = self.phrase_vectors[idx]

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

    def search_similar_phrases(self, query_text, limit=5):
        if not self.phrases:
            self.load_phrases_for_search()
        if not self.phrases:
            return []
        results = []
        for i, phrase in enumerate(self.phrases):
            similarity = self.calculate_similarity(query_text, phrase['phrase'], i)
            results.append({
                'id': phrase['id'],
                'phrase': phrase['phrase'],
                'author': phrase['author'],
                'description': phrase['description'],
                'similarity_score': similarity
            })
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]

    def search_similar_phrases_second(self, query_text, limit=5):
        if not self.phrases:
            self.load_phrases_for_search()
        if not self.phrases:
            return []
        results = []
        for i, phrase in enumerate(self.phrases):
            similarity = self.calculate_similarity_second(query_text, phrase['phrase'], i)
            results.append({
                'id': phrase['id'],
                'phrase': phrase['phrase'],
                'author': phrase['author'],
                'description': phrase['description'],
                'similarity_score': similarity
            })
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]

    def calculate_similarity_second(self, query_text, phrase_text, i):
        lev_ratio = difflib.SequenceMatcher(None, query_text.lower(), phrase_text.lower()).ratio()

        cos = 0.0
        if self.tfidf_matrix is not None:
            query_proc = self.preprocess_text(query_text)
            if query_proc:
                query_counter = Counter(query_proc.split())
                total_q = len(query_proc.split())
                query_vec = np.zeros(self.tfidf_matrix.shape[1])
                for word, freq in query_counter.items():
                    if word in self.word_to_idx:
                        idx = self.word_to_idx[word]
                        query_vec[idx] = (freq / total_q) * self.idf[idx]
                norm_q = np.linalg.norm(query_vec)
                norm_p = np.linalg.norm(self.tfidf_matrix[i])
                if norm_q > 0 and norm_p > 0:
                    cos = np.dot(query_vec, self.tfidf_matrix[i]) / (norm_q * norm_p)

        return (lev_ratio + cos) / 2


if __name__ == "__main__":
    searcher = PhraseSearcher()
    searcher.load_phrases_for_search()

    queries = [
        "дубина стоеросовая",  
        "трусливый заяц",      
        "умный семи пядей",    
        "язык без костей",     
        "стреляный воробей",   
        "жизнь берет",         
        "глупый человек",      
        "опытный человек",     
        "болтливый",
        "негр в пене",
        "Выставление небольшого успеха чем-то великим",
        "Вроде бы большое достижение, которое на самом деле малозначительно"
    ]

    for query in queries:
        print(f"Query: {query}")
        results = searcher.search_similar_phrases(query)
        results_second = searcher.search_similar_phrases_second(query)
        for res in results:
            print(f"Phrase: {res['phrase']}, Score: {res['similarity_score']:.4f}")
        print("---")
        for res in results_second:
            print(f"Phrase: {res['phrase']}, Score: {res['similarity_score']:.4f}")
        print("---")
