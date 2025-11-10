#!/bin/bash


# Создание функции

FUNCTION_NAME="for-serverless-aforism"
SOURCE_DIR="./backend"

ZIP_FUNCTION_NAME="function.zip"
RUNTIME="python312"

ENTRYPOINT="index.handler"

##  yc ydb database get --name DATABASE_NAME
## выдаст endpoint: grpcs://ydb.serverless.yandexcloud.net:2135/?database=/ru-centralX/{1}/{2}
## где grpcs://ydb.serverless.yandexcloud.net:2135 - эндпоинт
## /ru-centralX/{1}/{2} - DATABASE

YDB_ENDPOINT="grpcs://ydb.serverless.yandexcloud.net:2135" # в большинстве случаев так
YDB_DATABASE="/ru-centralX/{1}/{2}" #

pip install -r requirements.txt -t packages
zip -j $ZIP_FUNCTION_NAME $SOURCE_DIR/*

yc serverless function version create \
  --function-name=$FUNCTION_NAME \
  --runtime $RUNTIME \
  --entrypoint $ENTRYPOINT \
  --memory 1024m \
  --execution-timeout 30s \
  --source-path $ZIP_FUNCTION_NAME \
  --environment YDB_ENDPOINT=$YDB_ENDPOINT,YDB_DATABASE=$YDB_DATABASE

rm $ZIP_FUNCTION_NAME

# Загрузка статических файлов в Object Storage
BUCKET_NAME = "BUCKET_NAME"
aws s3api put-object --body index.html --bucket $BUCKET_NAME --key index.html
aws s3api put-object --body style.css --bucket $BUCKET_NAME --key style.css
aws s3api put-object --body script.js --bucket $BUCKET_NAME --key script.js

# создание API Gateway

yc serverless api-gateway create \
  --name for-serverless-aforism \
  --spec=for-serverless-aforism.yml \
  --description "for serverless aforism"