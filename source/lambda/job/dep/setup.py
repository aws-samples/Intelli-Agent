from setuptools import find_packages, setup

# align with the additional python modules in etl stack
setup(
    name="llm_bot_dep",
    version="0.1.0",
    packages=find_packages(exclude=[]),
    install_requires=[
        "langchain==0.1.0",
        "beautifulsoup4==4.12.2",
        "requests-aws4auth==1.2.3",
        "boto3==1.28.84",
        "openai==0.28.1",
        "pyOpenSSL==23.3.0",
        "tenacity==8.2.3",
        "markdownify==0.11.6",
        "mammoth==1.6.0",
        "chardet==5.2.0",
        "python-docx==1.1.0",
        "nltk==3.9.1",
        "pdfminer.six==20221105",
        "smart-open==7.0.4",
    ],
)
