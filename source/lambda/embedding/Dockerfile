FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.9

COPY requirements.txt  .
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY main.py ${LAMBDA_TASK_ROOT}
# TODO, pack the whole utils as pip package and multiplex with llm_bot_dep
COPY ./utils/* ${LAMBDA_TASK_ROOT}

CMD [ "main.lambda_handler" ]
