from common_utils.logger_utils  import get_logger
import json

logger = get_logger("retriever")

def lambda_handler(event, context=None):
    # '''
    # event: {
    #     "body": "{
    #         \"retrievers\": [
    #             {
    #                 \"type\": \"qq\",
    #                 \"workspace_ids\": [1],
    #                 \"top_k\": 10,
    #             },
    #             {
    #                 \"type\": \"qd\",
    #                 \"workspace_ids\": [4,5],
    #                 \"top_k\": 10,
    #             }
    #         ],
    #         \"rerankers\": [
    #             {
    #                 \"type\": \"reranker\",
    #                 \"top_k\": 10,
    #                 \"rerank_target_model\": \"bge_reranker_model.tar.gz\"
    #             }
    #         ],
    #         \"query\": \"What is the capital of France?\"
    #     }"
    # }
    # '''

    # response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    retriever_response = {
        "docs": [
            {
                "page_content": "Paris is the capital of France.", 
                "retrieval_score": 0.9,
                "rerank_score": 2.1,
            }
        ]
    }
    # response["body"] = retriever_response

    # print(f"finish retriever lambda invoke")
    # return response

    # event_body = event["body"]
    # state:dict = event_body['state']

    # logger.info(f'state: {json.dumps(state,ensure_ascii=False,indent=2)}')

    # response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    # state["is_context_enough"] = True
    # response["body"] = {"state": state}
    
    return {"code":0,"result":"原神"}

if __name__ == "__main__":
    print(lambda_handler({}, {}))