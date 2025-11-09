import os

from add_phrase import add_phrase_handler
from add_word import add_word_handler
from search_phrases import search_phrase_handler
from search_words import search_words_handler
from uuid import uuid4


BACKEND_VERSION = os.environ.get('BACKEND_VERSION', "v.3.0.1")
BACKEND_ID = str(uuid4())


def response(status_code: int, headers: dict[str, str], is_encoded: bool, body: str) -> dict:
    return {
        'statusCode': status_code,
        'headers': headers,
        'isBase64Encoded': is_encoded,
        'body': body,
        'BACKEND_ID': BACKEND_ID,
        'BACKEND_VERSION': BACKEND_VERSION
    }


def get_result(path, event, context):
    http_method = event.get('httpMethod')

    if http_method == 'GET':
        if path == "/phrase":
            return search_phrase_handler(event, context)
        if path == "/word":
            return search_words_handler(event, context)

    if http_method == 'POST':
        if path == "/phrase":
            return add_phrase_handler(event, context)
        if path == "/word":
            return add_word_handler(event, context)

    return response(404, {}, False, 'Данного пути не существует')


def handler(event, context):
    path = event.get('path')

    if path:
        if '?' in path:
            path = path.split('?')[0]

        return get_result(path, event, context)

    return response(404, {}, False, 'Эту функцию следует вызывать при помощи api-gateway')