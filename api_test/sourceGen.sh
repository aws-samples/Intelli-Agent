#!/bin/bash

yes | rm -rf ./biz_logic/rest_api/*
mkdir generated-client
chmod a+w ./generated-client

openapi-generator-cli generate -i Intelli-Agent-RESTful-API-prod-oas30.json -g python -o ./generated-client

mv ./generated-client/docs ./biz_logic/rest_api/
mv ./generated-client/openapi_client ./biz_logic/rest_api/

touch ./biz_logic/rest_api/__init__.py
sed -i '/__version__ = "1.0.0"/a\import sys\nimport os\nopenapi_client_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../biz_logic/rest_api"))\nsys.path.insert(0, openapi_client_path)\n' ./biz_logic/rest_api/openapi_client/__init__.py


rm -rf ./generated-client
