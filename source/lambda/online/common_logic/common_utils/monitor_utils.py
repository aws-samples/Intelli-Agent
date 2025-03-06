from shared.utils.logger_utils import get_logger

logger = get_logger(__name__)


def is_null_or_empty(value):
    if value is None:
        return True
    elif isinstance(value, (dict, list, str)) and not value:
        return True
    return False


def _file_name_in_path(file_path: str) -> str:
    return file_path.split("/")[-1]


def format_qq_data(data) -> str:
    """
    Formats QQ match result.

    Args:
        data (list): A list of dictionaries containing 'source', 'score', and 'page_content' keys.

    Returns:
        str: A markdown table string representing the formatted data.
    """
    if is_null_or_empty(data):
        return ""

    markdown_table = "**QQ Match Result**\n"
    markdown_table += "| Source | Score | Question | Answer |\n"
    markdown_table += "|-----|-----|-----|-----|\n"

    # Data contains only one QQ match result
    qq_source = _file_name_in_path(data.get("source", ""))
    qq_score = data.get("score", -1)
    qq_question = data.get("page_content", "").replace("\n", "<br>")
    qq_answer = data.get("answer", "").replace("\n", "<br>")
    markdown_table += f"| {qq_source} | {qq_score} | {qq_question} | {qq_answer} |\n"

    return markdown_table


def format_rag_data(data, qq_result) -> str:
    """
    Formats the given data into a markdown table.

    Args:
        data (list): A list of dictionaries containing 'source', 'score', and 'page_content' keys.
        qq_result (list): QQ match result

    Returns:
        str: A markdown table string representing the formatted data.
    """
    if is_null_or_empty(data):
        return ""

    markdown_table = "| Source File Name | Source URI | Score | RAG Context |\n"
    markdown_table += "|-----|-----|-----|-----|\n"
    for item in data:
        raw_source = item.get("source", "")
        source = _file_name_in_path(raw_source)
        score = item.get("score", -1)
        page_content = item.get("retrieval_content", "").replace("\n", "<br>")
        markdown_table += f"| {source} | {raw_source} | {score} | {page_content} |\n"

    if not is_null_or_empty(qq_result):
        markdown_table += "\n**QQ Match Result**\n"
        markdown_table += "| Source File Name | Source URI | Score | Question | Answer |\n"
        markdown_table += "|-----|-----|-----|-----|-----|\n"

        for qq_item in qq_result:
            raw_qq_source = qq_item.get("source", "")
            qq_source = _file_name_in_path(raw_qq_source)
            qq_score = qq_item.get("score", -1)
            qq_question = qq_item.get("page_content", "").replace("\n", "<br>")
            qq_answer = qq_item.get("answer", "").replace("\n", "<br>")
            markdown_table += f"| {qq_source} | {raw_qq_source} | {qq_score} | {qq_question} | {qq_answer} |\n"

    return markdown_table


def format_preprocess_output(ori_query, rewrite_query):
    if is_null_or_empty(ori_query) or is_null_or_empty(rewrite_query):
        return ""

    markdown_table = "| Original Query | Rewritten Query |\n"
    markdown_table += "|-------|-------|\n"
    markdown_table += f"| {ori_query} | {rewrite_query} |\n"

    return markdown_table


def format_intention_output(data):
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
