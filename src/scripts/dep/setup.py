from setuptools import setup, find_packages

setup(
    name='llm_bot_dep',
    version='0.1.0',
    packages=find_packages(exclude=[]),
    install_requires=[
        'langchain',
        'opensearch-py',
        # 'faiss_cpu',
        # 'sagemaker',
        'requests_aws4auth',
        'unstructured',
        'boto3',
        'nougat-ocr',
    ],
)