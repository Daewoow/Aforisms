import boto3

from backend.table_creater import TableHelper
from typing import Any


class WordTableHelper(TableHelper):
    def __init__(self):
        super().__init__()

    def create_table(self) -> Any:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=f"{self.DOCUMENT_API_URL}")

        table = ydb_docapi_client.create_table(
            TableName='aforisms_project/words',
            KeySchema=[
                {
                    'AttributeName': 'word_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'word',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'word_id',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'word',
                    'AttributeType': 'S'
                },

            ]
        )
        return table


if __name__ == '__main__':
    series_table = WordTableHelper().create_table()
    print("Table status:", series_table.table_status)
