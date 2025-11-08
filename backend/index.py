import asyncio

from add_phrase import add_phrase_handler
from add_word import add_word_handler
from search_phrases import search_phrase_handler
from search_words import search_words_handler


def response(status_code: int, headers: dict[str, str], is_encoded: bool, body: str) -> dict:
    return {
        'statusCode': status_code,
        'headers': headers,
        'isBase64Encoded': is_encoded,
        'body': body,
    }


async def get_result(path, event, context):
    http_method = event.get('httpMethod')

    if http_method == 'GET':
        if path == "/phrase":
            return await search_phrase_handler(event, context)
        if path == "/word":
            return await search_words_handler(event, context)

    if http_method == 'POST':
        if path == "/phrase":
            return await add_phrase_handler(event, context)
        if path == "/word":
            return await add_word_handler(event, context)

    return response(404, {}, False, 'Данного пути не существует')


def handler(event, context):
    path = event.get('path')

    if path:
        return asyncio.run(get_result(path, event, context))

    return response(404, {}, False, 'Эту функцию следует вызывать при помощи api-gateway')