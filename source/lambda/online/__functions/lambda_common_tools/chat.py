# give chat response
def lambda_handler(event_body,context=None):
    try:
        result = event_body['kwargs']['response']
        return {"code": 0, "result":result}
    except KeyError:
        return {"code": 1, "result": "The parameter “response” not found."}