import json
import logging
import os
from datetime import datetime

from backend.aforism_searcher import AforismSearcher
from db import YDBClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPLICA_ID = os.getenv('REPLICA_ID', 'replica-add')
BACKEND_VERSION = 'v1.0.0-python'


async def handler(event, context):
    """
    Функция для добавления новой фразы
    POST /api/add-phrase
    Body: { "phrase": "...", "author": "...", "description": "...", "source": "..." }
    """
    try:
        logger.info(f"Добавляем фраза: {REPLICA_ID}")
        ydb_client = YDBClient(AforismSearcher)
        if not hasattr(context, 'initialized'):
            await ydb_client.initialize_database()
            context.initialized = True
            logger.info(f"БД инициализирована на реплике: {REPLICA_ID}")

        try:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']

            phrase = body.get('phrase', '').strip()
            author = body.get('author', '').strip()
            description = body.get('description', '').strip()

            if not phrase or not author:
                logger.warning("Пропущена фраза или автор")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'
                    },
                    'body': json.dumps({
                        'error': 'Phrase and author are required fields',
                        'backend_id': REPLICA_ID,
                        'backend_version': BACKEND_VERSION
                    }, ensure_ascii=False)
                }

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Invalid request format: {str(e)}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'error': 'Invalid request format',
                    'backend_id': REPLICA_ID,
                    'backend_version': BACKEND_VERSION
                }, ensure_ascii=False)
            }

        result = await ydb_client.searcher.add_data(
            data=phrase,
            author=author,
            description=description or None
        )

        logger.info(f"Фраза добавлена успешно: {result['id']}")

        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'success': True,
                'phrase': result,
                'backend_id': REPLICA_ID,
                'backend_version': BACKEND_VERSION,
                'timestamp': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"Ошибка в данных: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'backend_id': REPLICA_ID,
                'backend_version': BACKEND_VERSION,
                'details': str(e)
            }, ensure_ascii=False)
        }
    