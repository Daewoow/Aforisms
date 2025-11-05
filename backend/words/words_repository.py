from botocore.exceptions import ClientError

from loader import Loader
from typing import Any
import boto3


class WordsRepository(Loader):
    def __init__(self):
        super().__init__()
        self.table_name = 'aforisms_project/words'

    def load_data(self, data) -> None:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=f"{self.DOCUMENT_API_URL}")

        table = ydb_docapi_client.Table(self.table_name)
        for document in data:
            word_id = int(document['word_id'])
            word = document['word']
            description = document['word_description']
            print("Words added:", word_id, word, description)
            table.put_item(Item=document)

    def put_word(self, word_id: int, word: str, word_description: str) -> Any:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=f"{self.DOCUMENT_API_URL}")

        table = ydb_docapi_client.Table(self.table_name)
        response = table.put_item(
            Item={
                'word_id': word_id,
                'word': word,
                'word_description': word_description
            }
        )
        return response

    def get_word(self, word_id: int, word: str) -> str:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=f"{self.DOCUMENT_API_URL}")

        table = ydb_docapi_client.Table(self.table_name)

        try:
            response = table.get_item(Key={'word_id': word_id, 'word': word})
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response['Item']

    def update_word(self, word_id: int, word: str, word_description: str) -> Any:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=self.DOCUMENT_API_URL)

        table = ydb_docapi_client.Table(self.table_name)

        response = table.update_item(
            Key={
                'word_id': word_id,
                'word': word
            },
            UpdateExpression="set word_description = :w",
            ExpressionAttributeValues={
                ':w': word_description
            },
            ReturnValues="UPDATED_NEW"
        )
        return response
