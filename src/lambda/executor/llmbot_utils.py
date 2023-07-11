

QA_SEP = "=>"
AWS_Free_Chat_Prompt = """你是云服务AWS的智能客服机器人{B}，能够回答{A}的各种问题以及陪{A}聊天，如:{chat_history}\n\n{A}: {question}\n{B}: """
AWS_Knowledge_QA_Prompt = """你是云服务AWS的智能客服机器人{B}，请严格根据反括号中的资料提取相关信息\n```\n{fewshot}\n```\n回答{A}的各种问题，比如:\n\n{A}: {question}\n{B}: """
Fewshot_prefix_Q="问题"
Fewshot_prefix_A="回答"

def combine_recalls(opensearch_knn_respose, opensearch_query_response):
    '''
    filter knn_result if the result don't appear in filter_inverted_result
    '''
    knn_threshold = 0.2
    inverted_theshold = 5.0
    filter_knn_result = { item["doc"] : item["score"] for item in opensearch_knn_respose if item["score"]> knn_threshold }
    filter_inverted_result = { item["doc"] : item["score"] for item in opensearch_query_response if item["score"]> inverted_theshold }

    combine_result = []
    for doc, score in filter_knn_result.items():
        if doc in filter_inverted_result.keys():
            combine_result.append({ "doc" : doc, "score" : score })

    return combine_result

def conversion_prompt_build(post_text, conversations, role_a, role_b):
    chat_history = [ """{}: {}\n{}: {}""".format(role_a, item[0], role_b, item[1]) for item in conversations ]
    chat_histories = "\n\n".join(chat_history)
    chat_histories = f'\n\n{chat_histories}' if len(chat_histories) else ""
    
    return AWS_Free_Chat_Prompt.format(chat_history=chat_histories, question=post_text, A=role_a, B=role_b)


def qa_knowledge_prompt_build(post_text, qa_recalls, role_a, role_b):
    """
    Detect User intentions, build prompt for LLM. For Knowledge QA, it will merge all retrieved related document paragraphs into a single prompt
    Parameters examples:
        post_text : "介绍下强化部件"
        qa_recalls: [ {"doc" : doc1, "score" : score}, ]
    return: prompt string
    """
    qa_pairs = [ obj["doc"].split(QA_SEP) for obj in qa_recalls ]
    qa_fewshots = [ "{}: {}\n{}: {}".format(Fewshot_prefix_Q, pair[0], Fewshot_prefix_A, pair[1]) for pair in qa_pairs ]
    fewshots_str = "\n\n".join(qa_fewshots[-3:])
    return AWS_Knowledge_QA_Prompt.format(fewshot=fewshots_str, question=post_text, A=role_a, B=role_b)
