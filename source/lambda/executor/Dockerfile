FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.9

COPY requirements.txt  .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY main.py ${LAMBDA_TASK_ROOT}

# recursively copy the files and subdirectories from utils to the lambda task root
COPY utils ${LAMBDA_TASK_ROOT}

CMD [ "main.lambda_handler" ]
