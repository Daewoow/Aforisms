from decimal import Decimal

from botocore.exceptions import ClientError

from backend.loader import Loader
from typing import Any
import json
import boto3


class AforismsRepository(Loader):
    def __init__(self):
        super().__init__()
        self.table_name = 'aforisms_project/aforisms'

    def load_data(self, data) -> None:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=f"{self.DOCUMENT_API_URL}")

        table = ydb_docapi_client.Table(self.table_name)
        for document in data:
            word_id = int(document['aforism_id'])
            word = document['aforism']
            author = document['aforism_author']
            description = document['aforism_description']
            print("Aforisms added:", word_id, word, description, author)
            table.put_item(Item=document)

    def put_word(self, aforism_id: int, aforism: str, aforism_author: str, aforism_description: str) -> Any:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=f"{self.DOCUMENT_API_URL}")

        table = ydb_docapi_client.Table(self.table_name)
        response = table.put_item(
            Item={
                'aforism_id': aforism_id,
                'aforism': aforism,
                'aforism_author': aforism_author,
                'aforism_description': aforism_description
            }
        )
        return response

    def get_aforism(self, aforism_id: int, aforism: str) -> str:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=f"{self.DOCUMENT_API_URL}")

        table = ydb_docapi_client.Table(self.table_name)

        try:
            response = table.get_item(Key={'aforism_id': aforism_id, 'aforism': aforism})
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response['Item']

    def update_aforism(self, aforism_id: int, aforism: str, aforism_author: str, aforism_description: str) -> Any:
        ydb_docapi_client = boto3.resource('dynamodb', endpoint_url=self.DOCUMENT_API_URL)

        table = ydb_docapi_client.Table(self.table_name)

        response = table.update_item(
            Key={
                'aforism_id': aforism_id,
                'aforism': aforism
            },
            UpdateExpression="set aforism_author = :a, aforism_description = :d",
            ExpressionAttributeValues={
                ':d': aforism_description,
                ':a': aforism_author
            },
            ReturnValues="UPDATED_NEW"
        )
        return response
