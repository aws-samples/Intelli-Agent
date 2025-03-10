from shared.utils.logger_utils import get_logger
from typing import List
from langchain_core.documents import Document
logger = get_logger(__name__)


def is_null_or_empty(value):
    if value is None:
        return True
    elif isinstance(value, (dict, list, str)) and not value:
        return True
    return False


def _file_name_in_path(file_path: str) -> str:
    return file_path.split("/")[-1]


def format_qq_data(doc:Document,source_field,rerank_score_field="relevance_score") -> str:
    """
    Formats QQ match result.

    Args:
        data (list): A list of dictionaries containing 'source', 'score', and 'page_content' keys.

    Returns:
        str: A markdown table string representing the formatted data.
    """
    if is_null_or_empty(doc):
        return ""

    markdown_table = "**QQ Match Result**\n"
    markdown_table += "| Source | Score | Question | Answer |\n"
    markdown_table += "|-----|-----|-----|-----|\n"

    # Data contains only one QQ match result
    qq_source = _file_name_in_path(doc.metadata.get(source_field, ""))
    score = doc.metadata.get("score", -1)
    rerank_score = doc.metadata.get(rerank_score_field, None)
    if rerank_score is not None:
        score = f"{doc.metadata['search_by']} score: {score}, rerank score: {rerank_score})"
    else:
        score = f"{doc.metadata['search_by']} score: {score}"
    qq_question = doc.page_content.replace("\n", "<br>")
    qq_answer = doc.metadata.get("answer", "").replace("\n", "<br>")
    markdown_table += f"| {qq_source} | {score} | {qq_question} | {qq_answer} |\n"

    return markdown_table


def format_rag_data(retrieved_contexts:List[Document], qq_result:List[Document],source_field:str,rerank_score_field="relevance_score") -> str:
    """
    Formats the given data into a markdown table.

    Args:
        data (list): A list of dictionaries containing 'source', 'score', and 'page_content' keys.
        qq_result (list): QQ match result

    Returns:
        str: A markdown table string representing the formatted data.
    """
    if is_null_or_empty(retrieved_contexts):
        return ""

    markdown_table = "| Source File Name | Source URI | Score | RAG Context |\n"
    markdown_table += "|-----|-----|-----|-----|\n"
    for item in retrieved_contexts:
        raw_source = item.metadata.get(source_field, "")
        source = _file_name_in_path(raw_source)
        score = item.metadata.get("score", -1)
        rerank_score = item.metadata.get(rerank_score_field, None)
        if rerank_score is not None:
            score = f"{item.metadata['search_by']} score: {score}, rerank score: {rerank_score})"
        else:
            score = f"{item.metadata['search_by']} score: {score}"

        page_content = item.page_content.replace("\n", "<br>")
        markdown_table += f"| {source} | {raw_source} | {score} | {page_content} |\n"

    if not is_null_or_empty(qq_result):
        markdown_table += "\n**QQ Match Result**\n"
        markdown_table += "| Source File Name | Source URI | Score | Question | Answer |\n"
        markdown_table += "|-----|-----|-----|-----|-----|\n"

        for qq_item in qq_result:
            raw_qq_source = item.metadata.get(source_field, "")
            qq_source = _file_name_in_path(raw_qq_source)

            score = item.metadata.get("score", -1)
            rerank_score = item.metadata.get(rerank_score_field, None)
            if rerank_score is not None:
                score = f"{item.metadata['search_by']} score: {score}, rerank score: {rerank_score})"
            else:
                score = f"{item.metadata['search_by']} score: {score}"

            # qq_score = qq_item.get("score", -1)
            qq_question = qq_item.page_content.replace("\n", "<br>")
            qq_answer = qq_item.metadata.get("answer", "").replace("\n", "<br>")
            markdown_table += f"| {qq_source} | {raw_qq_source} | {score} | {qq_question} | {qq_answer} |\n"

    return markdown_table


def format_preprocess_output(ori_query, rewrite_query):
    if is_null_or_empty(ori_query) or is_null_or_empty(rewrite_query):
        return ""

    markdown_table = "| Original Query | Rewritten Query |\n"
    markdown_table += "|-------|-------|\n"
    markdown_table += f"| {ori_query} | {rewrite_query} |\n"

    return markdown_table


def format_intention_output(data:List[Document]):
    if is_null_or_empty(data):
        return ""

    markdown_table = "| Query | Score | Name | Intent | Additional Info |\n"
    markdown_table += "|-------|-------|-------|-------|-------|\n"
    for item in data:
        query = item.get("query", "")
        score = item.get("score", "")
        name = item.get("name", "")
        intent = item.get("intent", "")
        kwargs = ', '.join(
            [f'{k}: {v}' for k, v in item.get('kwargs', {}).items()])
        markdown_table += f"| {query} | {score} | {name} | {intent} | {kwargs} |\n"

    return markdown_table
