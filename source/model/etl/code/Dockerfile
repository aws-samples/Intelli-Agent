FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-gpu-py310-cu118-ubuntu20.04-sagemaker

RUN apt update \
    && apt install -y --no-install-recommends wget python3 python3-pip \
    && ln -sf python3 /usr/bin/python \
    && ln -sf pip3 /usr/bin/pip \
    && pip install --upgrade pip \
    && pip install wheel setuptools \
    && apt-get install -y git

RUN apt install -y tesseract-ocr
RUN apt install -y tesseract-ocr-chi-sim
RUN apt-get install -y poppler-utils

ARG FUNCTION_DIR="/opt/ml/code"
ADD / ${FUNCTION_DIR}/
RUN pip3 install -r ${FUNCTION_DIR}/requirements.txt
RUN pip3 install flask gevent

WORKDIR ${FUNCTION_DIR}
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PYTHONIOENCODING="utf8"

# Command can be overwritten by providing a different command in the template directly.
ENTRYPOINT ["python", "sm_predictor.py"]