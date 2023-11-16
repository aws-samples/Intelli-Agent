from djl_python import Input, Output

import os
import boto3
import logging
import datetime
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3 = boto3.client("s3")

def upload_chunk_to_s3(logger_content: str, bucket: str, prefix: str, splitting_type: str):
    """Upload the logger file to S3 with hierachy below:
    filename A
        ├── before-splitting
        │   ├── timestamp 1
        │   │   ├── logger file 1
        │   ├── timestamp 2
        │   │   ├── logger file 2
        ├── semantic-splitting
        │   ├── timestamp 3
        │   │   ├── logger file 3
        │   ├── timestamp 4
        │   │   ├── logger file 4
        ├── chunk-size-splitting
        │   ├── timestamp 5
        │   │   ├── logger file 5
        │   ├── timestamp 6
        │   │   ├── logger file 6
    filename B
        ├── before-splitting
        │   ├── timestamp 7
        │   │   ├── logger file 7
        │   ├── timestamp 8
        │   │   ├── logger file 8
        ├── semantic-splitting
        │   ├── timestamp 9
        │   │   ├── logger file 9
        │   ├── timestamp 10
        │   │   ├── logger file 10
        ├── chunk-size-splitting
        │   ├── timestamp 11
        │   │   ├── logger file 11
        │   ├── timestamp 12
        │   │   ├── logger file 12
        ...
    """
    # round the timestamp to hours to avoid too many folders
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    # make the logger file name unique
    object_key = f"{prefix}/{splitting_type}/{timestamp}/{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.log"
    try:
        res = s3.put_object(Bucket=bucket, Key=object_key, Body=logger_content)
        logger.info(f"Upload logger file to S3: {res}")
        return f"s3://{bucket}/{object_key}"
    except Exception as e:
        logger.error(f"Error uploading logger file to S3: {e}")
        return None

def nougat(file_path: Path) -> str:
    """Executes the `nougat` command to convert the specified PDF file to Markdown format.

    Args:
        file_path (Path): The path to the PDF file to be converted.

    Returns:
        str: The Markdown content resulting from the `nougat` conversion.
    """
    # nougat ./paperSnapshot.pdf --full-precision --markdown -m 0.1.0-base -o tmp --recompute
    cli_command = ["nougat", str(file_path), "full-precision", "--markdown", "-m", "0.1.0-base", "-o", "/tmp", "--recompute"]

    try:
        result = subprocess.run(
            cli_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        result.check_returncode()
        return result.stdout

    except subprocess.CalledProcessError as e:
        logger.info(
            f"Nougat command failed with return code {e.returncode}: {e.stderr}"
        )
        raise RuntimeError("Nougat command failed.") from e

def process_pdf(bucket, object_key, destination_bucket, **kwargs):
    """
    Process a given PDF file and extracts structured information from it.

    This function reads a PDF file, converts it to HTML using PDFMiner, then extracts 
    and structures the information into a list of dictionaries containing headings and content.

    Parameters:
    s3 (boto3.client): The S3 client to use for downloading the PDF file.
    pdf (bytes): The PDF file to process.
    **kwargs: Arbitrary keyword arguments. The function expects 'bucket' and 'key' among the kwargs
              to specify the S3 bucket and key where the PDF file is located.

    Returns:
    list[Doucment]: A list of Document objects, each representing a semantically grouped section of the PDF file. Each Document object contains a metadata defined in metadata_template, and page_content string with the text content of that section.
    """

    local_path = str(os.path.basename(object_key))
    local_path = f"/tmp/{local_path}"
    # download to local for futher processing
    logger.info(f"Downloading {object_key} to {local_path}")
    s3.download_file(Bucket=bucket, Key=object_key, Filename=local_path)

    nougat(local_path)

    # Rest of your code for reading and processing the output
    file_path = Path(local_path)
    output_path = Path("/tmp") / f"{file_path.stem}.mmd"
    with output_path.open("r") as f:
        content = f.read()
    
    filename = file_path.stem
    destination_s3_path = upload_chunk_to_s3(content, destination_bucket, filename, "before-splitting")

    return destination_s3_path


def handle(inputs: Input):

    if inputs.is_empty():
        return None
    data = inputs.get_as_json()
    
    bucket = data["s3_bucket"]
    object_key = data["object_key"]

    destination_bucket = data["destination_bucket"]

    logging.info(f"Processing bucket: {bucket}, object_key: {object_key}")

    destination_path = process_pdf(bucket, object_key, destination_bucket)

    result = {
        "destination_path": destination_path
    }

    return Output().add_as_json(result)
