

from .text import process_text
from .csv import process_csv
from .html import process_html
from .pdf import process_pdf
from .image import process_image

def cb_process_object(s3, file_type: str, file_content, **kwargs):
    res = None
    if file_type == 'txt':
        res = process_text(file_content, **kwargs)
    elif file_type == 'csv':
        res = process_csv(s3, file_content, **kwargs)
    elif file_type == 'html':
        process_html(s3, file_content, **kwargs)
    elif file_type == 'pdf':
        # res = post_process_pdf(process_pdf(file_content, **kwargs))
        res = process_pdf(s3, file_content, **kwargs)
    elif file_type == 'image':
        process_image(s3, file_content, **kwargs)

    return res