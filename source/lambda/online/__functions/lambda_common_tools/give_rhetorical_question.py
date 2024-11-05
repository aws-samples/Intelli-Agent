# give rhetorical question
def lambda_handler(event_body,context=None):
    try:
        result = event_body['kwargs']['question']
        return {"code": 0, "result":result}
    except KeyError:
        return {"code": 1, "result": "The parameter “question” not  found."}