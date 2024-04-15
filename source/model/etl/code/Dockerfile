FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04

RUN apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends unzip build-essential wget python3 python3-pip \
    && ln -sf python3 /usr/bin/python \
    && ln -sf pip3 /usr/bin/pip \
    && pip install --upgrade pip \
    && pip install wheel setuptools

ARG FUNCTION_DIR="/opt/ml/code/"
ARG MODEL_DIR="/opt/ml/model/"
ENV MODEL_PATH=${MODEL_DIR}

ARG LAYOUT_MODEL_URL="https://aws-gcr-solutions-assets.s3.cn-northwest-1.amazonaws.com.cn/ai-solution-kit/layout-analysis/1.4.0"
RUN mkdir -p ${MODEL_DIR} && wget -c $LAYOUT_MODEL_URL/layout_weight_llm.zip -O ${MODEL_DIR}/layout_weight_llm.zip
RUN unzip ${MODEL_DIR}/layout_weight_llm.zip -d ${MODEL_DIR} && rm -rf ${MODEL_DIR}/layout_weight_llm.zip

ADD / ${FUNCTION_DIR}/

RUN pip3 install -r ${FUNCTION_DIR}/requirements.txt
WORKDIR ${FUNCTION_DIR}
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PYTHONIOENCODING="utf8"

# Command can be overwritten by providing a different command in the template directly.
ENTRYPOINT ["python", "sm_predictor.py"]