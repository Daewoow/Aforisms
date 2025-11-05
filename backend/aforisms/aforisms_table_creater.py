import boto3

from backend.table_creater import TableHelper
from typing import Any


class AforismTableHelper(TableHelper):
    def __init__(self):
        super().__init__()

    def create_table(self) -> Any:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=f"{self.DOCUMENT_API_URL}")

        table = ydb_docapi_client.create_table(
            TableName='aforisms_project/aforisms',
            KeySchema=[
                {
                    'AttributeName': 'aforism_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'aforism',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'aforism_id',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'aforism',
                    'AttributeType': 'S'
                },

            ]
        )
        return table

