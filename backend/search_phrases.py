import json
import logging
import os
from datetime import datetime
from db import ydb_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPLICA_ID = os.getenv('REPLICA_ID', 'replica-1')
BACKEND_VERSION = 'v1.0.0-python'


async def search_phrase_handler(event, context):
    """
    Функция для поиска афоризмов
    GET /phrase
    Body: { "phrase": "...", "author": "...", "description": "..." }
    """
    try:
        logger.info(f"Ищем в реплике {REPLICA_ID}")

        if not hasattr(context, 'initialized'):
            await ydb_client.initialize_database()
            context.initialized = True
            logger.info(f"БД и модели инициализированы на реплике {REPLICA_ID}")

        try:
            query_text = event.get('queryStringParameters', {}).get('text', '').strip()

            if not query_text:
                logger.warning("Пустой текст")
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                                'Access-Control-Allow-Headers': 'Content-Type'},
                    'body': json.dumps({'error': 'Text for search is required', 'backend_id': REPLICA_ID,
                                        'backend_version': BACKEND_VERSION}, ensure_ascii=False)
                }

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'POST, OPTIONS',
                            'Access-Control-Allow-Headers': 'Content-Type'},
                'body': json.dumps(
                    {
                        'error': f'Invalid request format{e}',
                        'backend_id': REPLICA_ID,
                        'backend_version': BACKEND_VERSION
                    },
                    ensure_ascii=False)
            }

        phrases = await ydb_client.aforism_searcher.search_similar_data(query_text, limit=5)

        logger.info(f"Найдено {len(phrases)} похожих фраз: '{query_text}'")
        response = {
            'query_text': query_text,
            'phrases': phrases,
            'backend_id': REPLICA_ID,
            'backend_version': BACKEND_VERSION,
            'timestamp': datetime.utcnow().isoformat()
        }

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'},
            'body': json.dumps(response, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"Error in search_phrases: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type'},
            'body': json.dumps(
                {'error': 'Internal server error', 'backend_id': REPLICA_ID, 'backend_version': BACKEND_VERSION,
                 'details': str(e)}, ensure_ascii=False)
        }
