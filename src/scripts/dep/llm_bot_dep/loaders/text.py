import re

def pre_process_text(text: str):
    # Remove special characters, punctuation, line breaks and multiple spaces with a single space,
    str_doc = re.sub(r'[^\w\s]', '', text)
    str_doc = re.sub(r'\s+', ' ', str_doc)
    str_doc = re.sub(r'\n', ' ', str_doc)
    return str_doc.strip()


def process_text(text: str):
    text = pre_process_text(text)