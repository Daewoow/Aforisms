# Aforisms
Веб-приложение, которое по описанию найдёт Вам нужное слово/афоризм. Развёрнуто при помощи serverless-технологий.

Скрипт для добавления статических файлов в Object Storage:
```shell
#!/bin/bash

BUCKET_NAME = "BUCKET_NAME"
aws s3api put-object --body index.html --bucket $BUCKET_NAME --key index.html
aws s3api put-object --body style.css --bucket $BUCKET_NAME --key style.css
aws s3api put-object --body script.js --bucket $BUCKET_NAME --key script.js
```

Скрипт для создания API Gateway:
```shell
#!/bin/bash
yc serverless api-gateway create \
  --name for-serverless-aforism \
  --spec=for-serverless-aforism.yml \
  --description "for serverless aforism"
```

Скрипт для обновления(развёртывания) функции:
```shell
#!/bin/bash
FUNCTION_NAME="for-serverless-aforism"
SOURCE_DIR="./backend"
ZIP_FUNCTION_NAME="function.zip"
RUNTIME="python312"
ENTRYPOINT="index.handler"

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
```

Скрипт для применения схемы YDB:
```shell
#!/bin/bash
YDB_ENDPOINT="grpcs://ydb.serverless.yandexcloud.net:2135" # в большинстве случаев так
YDB_DATABASE="/ru-centralX/{1}/{2}" #

SCHEMA_FILE="ydb_schema.yql"

ydb -e $YDB_ENDPOINT -d $YDB_DATABASE \
  --auth-token "$(yc iam create-token)" \
  scheme ls

ydb -e $YDB_ENDPOINT -d $YDB_DATABASE \
  --auth-token "$(yc iam create-token)" \
  scripting yql -f $SCHEMA_FILE
```