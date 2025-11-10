#!/bin/bash

## yc ydb database get --name DATABASE_NAME
## выдаст endpoint: grpcs://ydb.serverless.yandexcloud.net:2135/?database=/ru-centralX/{1}/{2}
## где grpcs://ydb.serverless.yandexcloud.net:2135 - эндпоинт
## /ru-centralX/{1}/{2} - DATABASE

YDB_ENDPOINT="grpcs://ydb.serverless.yandexcloud.net:2135" # в большинстве случаев так
YDB_DATABASE="/ru-centralX/{1}/{2}" #

SCHEMA_FILE="ydb_schema.yql"

ydb -e $YDB_ENDPOINT -d $YDB_DATABASE \
  --auth-token "$(yc iam create-token)" \
  scheme ls

ydb -e $YDB_ENDPOINT -d $YDB_DATABASE \
  --auth-token "$(yc iam create-token)" \
  scripting yql -f $SCHEMA_FILE

# Либо же через WEB-интерфейс YDB Manager
