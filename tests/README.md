# llm-bot-api-test

## Description

This project helps you quickly build a test environment with the **same structure** as **test pipeline** in your local
environment.

# References

You may need to refer to the following documents:

- Test locally

## Build Test Environment

If the shell fails, please refer to the `local_build.sh` file and execute the commands step by step.

```bash
make build
```

## Setup Environment Variables

Create `.env` file with the following content:

```bash
API_GATEWAY_URL=https://xxx.execute-api.ap-northeast-1.amazonaws.com/v1/
API_BUCKET=llm-bot-documents-xxx
```

## Run All Tests

```bash
make test
```

## Run Specific Directory/File/Class/Case

```bash
# test directory
make test test_01_api_common_entry/
# test file
make test test_01_api_common_entry/test_01_restful_api.py
# test class
make test test_01_api_common_entry/test_01_restful_api.py/test_1_common_entry_restful_api
```