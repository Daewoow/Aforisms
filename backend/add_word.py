import json
import logging
import os
from datetime import datetime
from db import ydb_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPLICA_ID = os.getenv('REPLICA_ID', 'replica-add-word')
BACKEND_VERSION = 'v1.0.0-python'


def add_word_handler(event, context):
    """
    Функция для добавления нового слова
    POST /word
    Body: { "word": "...", "description": "..." }
    """
    try:
        logger.info(f"Добавляем слово: {REPLICA_ID}")

        try:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']

            word = body.get('word', '').strip()
            description = body.get('description', '').strip()

            if not word or not description:
                logger.warning("Пропущено слово или описание")
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                                'Access-Control-Allow-Headers': 'Content-Type'},
                    'body': json.dumps({
                        'error': 'Word and description are required fields',
                        'backend_id': REPLICA_ID,
                        'backend_version': BACKEND_VERSION
                    }, ensure_ascii=False)
                }

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            return {'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                                'Access-Control-Allow-Headers': 'Content-Type'}, 'body': json.dumps(
                    {'error': 'Invalid request format', 'backend_id': REPLICA_ID, 'backend_version': BACKEND_VERSION},
                    ensure_ascii=False)}

        result = ydb_client.word_searcher.add_data(
            word=word,
            description=description
        )

        logger.info(f"Слово добавлено успешно: {result['id']}")

        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'},
            'body': json.dumps({
                'success': True,
                'word': result,
                'backend_id': REPLICA_ID,
                'backend_version': BACKEND_VERSION,
                'timestamp': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }
    except Exception as e:
        logger.error(f"Ошибка в данных: {str(e)}", exc_info=True)
        return {'statusCode': 500, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                                               'Access-Control-Allow-Methods': 'POST, OPTIONS',
                                               'Access-Control-Allow-Headers': 'Content-Type'},
                'body': json.dumps({'error': 'Internal server error', 'backend_id': REPLICA_ID,
                                    'backend_version': BACKEND_VERSION, 'details': str(e)}, ensure_ascii=False)}
