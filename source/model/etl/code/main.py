
import os
# os.environ["DEFAULT_PADDLE_LANG"] = "ch"
# os.environ["OCR_AGENT"] = "paddle"

import json
import boto3
import logging
import datetime
import subprocess
from pathlib import Path
from unstructured.partition.pdf import partition_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3 = boto3.client("s3")

def get_element_size(element):
    """Get the size of the element.

    Args:
        element : The element to get the width from.

    """

    points = element.metadata.coordinates.points
    element_width = points[2][0] - points[0][0]
    element_height = points[2][1] - points[0][1]
    return (element_width, element_height)

def sorted_elements(elements, same_line_threshold):
    """
    Sort text boxes in order from top to bottom, left to right
    The points in elements follows this order:
    (upper_left, lower_left, lower_right, upper_right)
    Each point is (x, y)
    args:
        dt_boxes(array):detected text boxes with shape [4, 2]
    return:
        sorted boxes(array) with shape [4, 2]
    """

    num_elements = len(elements)
    sorted_elements = sorted(elements, key=lambda x: (x.metadata.coordinates.points[0][1], x.metadata.coordinates.points[0][0]))
    _elements = list(sorted_elements)

    cur_index = 0
    while cur_index < num_elements:
        cur_element_points = _elements[cur_index].metadata.coordinates.points
        next_index = cur_index + 1
        while next_index < num_elements:
            next_element_points = _elements[next_index].metadata.coordinates.points
            if abs(next_element_points[0][1] - cur_element_points[0][1]) < same_line_threshold:
                next_index += 1
            else:
                break
        if next_index - cur_index > 1:
            _elements[cur_index:next_index] = sorted(_elements[cur_index:next_index], key=lambda x: x.metadata.coordinates.points[0][0])
       
        cur_index = next_index 

    return _elements

def get_page_numbers(elements):
    """
    Get all the page numbers from the elements.
    """
    page_numbers = []
    for element in elements:
        if element.metadata.page_number not in page_numbers:
            page_numbers.append(element.metadata.page_number)
    return page_numbers

def get_elements_by_page(elements, page_number):
    """
    Get the elements for a specific page.
    """
    elements_by_page = []
    for element in elements:
        if element.metadata.page_number == page_number:
            elements_by_page.append(element)
    return elements_by_page

def get_element_diff(element1, element2):
    """
    Get the difference between two elements.
    """
    element1_points = element1.metadata.coordinates.points
    element1_medium_point = ((element1_points[0][0] + element1_points[2][0]) / 2, (element1_points[0][1] + element1_points[2][1]) / 2)
    element2_points = element2.metadata.coordinates.points
    element2_medium_point = ((element2_points[0][0] + element2_points[2][0]) / 2, (element2_points[0][1] + element2_points[2][1]) / 2)
    x_diff = element2_medium_point[0] - element1_medium_point[0]
    y_diff = element2_medium_point[1] - element1_medium_point[1]

    return x_diff, y_diff

def get_title_threshold(elements):
    """
    Unstructured Library usually generates tons of titles from the pdf,
    we need to remove the duplicate titles and keep less than 5% elements with biggest.
    """
    all_element_height = []
    for element in elements:
        all_element_height.append(get_element_size(element)[0])
    all_element_height.sort(reverse=True)

    # Get the threshold for being a Title(top 5%)
    title_threshold = all_element_height[int(len(all_element_height) * 0.05)]
    subtitle_threshold = all_element_height[int(len(all_element_height) * 0.15)]
    text_threshold = all_element_height[int(len(all_element_height) * 0.5)]
    return title_threshold, subtitle_threshold, text_threshold

def transform_elements_to_markdown(elements):
    """Transform the list of elements to markdown content.

    Sample input: 
    [   
        <unstructured.documents.elements.Title object>, 
        <unstructured.documents.elements.NarrativeText object>, 
        <unstructured.documents.elements.Title object>, 
        <unstructured.documents.elements.Text object>, 
        <unstructured.documents.elements.Text object>
    ]

    Sample output:
    [
        "# Title 1\n\n",
        "Narrative text 1\n\n",
        "# Title 2\n\n",
        "Text 1\n\n",
        "Text 2\n\n"
    ]

    Args:
        elements (List[Dict]): The list of elements to be transformed.

    Returns:
        List[str]: The list of Markdown strings resulting from the transformation.
    """
    
    # Implementation of a Naive Markdown converter
    # TODO: Add support for Tables by analyzing the layout
    markdown_content = []
    title_threshold, subtitle_threshold, text_threshold = get_title_threshold(elements)
    same_line_threshold = text_threshold * 0.5

    page_numbers = get_page_numbers(elements)
    sorted_page_numbers = sorted(page_numbers)

    for page_number in sorted_page_numbers:
        raw_page_elements = get_elements_by_page(elements, page_number)
        page_elements = sorted_elements(raw_page_elements, same_line_threshold)

        for page_element_id, page_element in enumerate(page_elements):
            if page_element_id > 0:
                prev_page_element = page_elements[page_element_id - 1]
                x_diff, y_diff = get_element_diff(prev_page_element, page_element)
                if x_diff > 0 and y_diff < same_line_threshold:
                    prev_markdown_content = markdown_content.pop()
                    if prev_markdown_content.strip().endswith("|"):
                        markdown_content.append(f"{prev_markdown_content.strip()}")
                    else:
                        markdown_content.append(f"|{prev_markdown_content.strip()}|")
                    markdown_content.append(f"{page_element.text}|\n\n")
                    continue


            if page_element.category == "Title":
                if get_element_size(page_element)[0] > title_threshold:
                    markdown_content.append(f"# {page_element.text}\n\n")
                elif get_element_size(page_element)[0] > subtitle_threshold:
                    markdown_content.append(f"## {page_element.text}\n\n")
                elif get_element_size(page_element)[0] > text_threshold:
                    markdown_content.append(f"### {page_element.text}\n\n")
                else:
                    markdown_content.append(f"{page_element.text}\n\n")
            elif page_element.category == "NarrativeText":
                markdown_content.append(f"{page_element.text}\n\n")
            elif page_element.category == "UncategorizedText":
                markdown_content.append(f"{page_element.text}\n\n")
            elif page_element.category in ["List", "ListItem", "List-item"]:
                markdown_content.append(f"* {page_element.text}\n\n")
            elif page_element.category == "Table":
                markdown_content.append(page_element.metadata.text_as_html if page_element.metadata.text_as_html else "")
            else:
                markdown_content.append(f"{page_element.text}\n\n")

    return markdown_content

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
        return object_key
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

def unstructured(file_path: Path) -> str:
    elements = partition_pdf(filename=file_path, languages = ["eng", "chi_sim"])
    markdown_content_list = transform_elements_to_markdown(elements)

    return markdown_content_list

def process_pdf(bucket, object_key, destination_bucket, mode = 'unstructured', **kwargs):
    """
    Process a given PDF file and extracts structured information from it.
    
    Args:
        bucket (str): The name of the S3 bucket where the PDF file is located.
        object_key (str): The key of the PDF file in the S3 bucket.
        destination_bucket (str): The name of the S3 bucket where the output should be uploaded.
        mode (str): The mode of processing. Can be either `unstructured` or `nougat`.
        
    Returns:
        str: The S3 prefix where the output is located.
    """

    local_path = str(os.path.basename(object_key))
    local_path = f"/tmp/{local_path}"
    file_path = Path(local_path)
    # download to local for futher processing
    logger.info(f"Downloading {object_key} to {local_path}")
    s3.download_file(Bucket=bucket, Key=object_key, Filename=local_path)

    if mode == 'nougat':
        nougat(local_path)
        # Rest of your code for reading and processing the output
        output_path = Path("/tmp") / f"{file_path.stem}.mmd"
        with output_path.open("r") as f:
            content = f.read()
    else:
        markdown_content_list = unstructured(local_path)
        content = "".join(markdown_content_list)
    
    filename = file_path.stem
    destination_s3_path = upload_chunk_to_s3(content, destination_bucket, filename, "before-splitting")

    return destination_s3_path


def process_pdf_pipeline(body):
    
    bucket = body["s3_bucket"]
    object_key = body["object_key"]
    destination_bucket = body["destination_bucket"]
    mode = body["mode"]

    logging.info(f"Processing bucket: {bucket}, object_key: {object_key}")

    destination_prefix = process_pdf(bucket, object_key, destination_bucket, mode)

    result = {
        "destination_prefix": destination_prefix
    }

    return result
