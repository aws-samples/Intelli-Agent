import json
import boto3

def get_session(session_id, chat_session_table):

    table_name = chat_session_table
    dynamodb = boto3.resource('dynamodb')

    # table name
    table = dynamodb.Table(table_name)
    operation_result = ""

    response = table.get_item(Key={'session-id': session_id})

    if "Item" in response.keys():
        # print("****** " + response["Item"]["content"])
        operation_result = json.loads(response["Item"]["content"])
    else:
        # print("****** No result")
        operation_result = ""

    return operation_result


# param:    session_id
#           question
#           answer
# return:   success
#           failed
def update_session(session_id, chat_session_table, question, answer, intention):

    table_name = chat_session_table
    dynamodb = boto3.resource('dynamodb')

    # table name
    table = dynamodb.Table(table_name)
    operation_result = ""

    response = table.get_item(Key={'session-id': session_id})

    if "Item" in response.keys():
        # print("****** " + response["Item"]["content"])
        chat_history = json.loads(response["Item"]["content"])
    else:
        # print("****** No result")
        chat_history = []

    chat_history.append([question, answer, intention])
    content = json.dumps(chat_history)

    # inserting values into table
    response = table.put_item(
        Item={
            'session-id': session_id,
            'content': content
        }
    )

    if "ResponseMetadata" in response.keys():
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            operation_result = "success"
        else:
            operation_result = "failed"
    else:
        operation_result = "failed"

    return operation_result