from setuptools import find_packages, setup

# align with the additional python modules in etl stack
setup(
    name="llm_bot_dep",
    version="0.1.0",
    packages=find_packages(exclude=[]),
    package_data={
        "": [
            "*.txt",
            "*.json",
        ],  # include all .txt and .json files in any package
        # Or if you want to be more specific:
        # "your_package_name": ["data/*.txt", "config/*.json"]
    },
    include_package_data=True,  # This tells setuptools to include package_data
    install_requires=[
        "langchain==0.3.7",
        "beautifulsoup4==4.12.2",
        "requests-aws4auth==1.2.3",
        "boto3==1.35.98",
        "openai==1.63.2",
        "pyOpenSSL==23.3.0",
        "tenacity==8.2.3",
        "markdownify==0.11.6",
        "mammoth==1.6.0",
        "chardet==5.2.0",
        "python-docx==1.1.0",
        "pdfminer.six==20221105",
        "smart-open==7.0.4",
        "pillow==10.0.1",
        "tiktoken==0.8.0",
    ],
)
