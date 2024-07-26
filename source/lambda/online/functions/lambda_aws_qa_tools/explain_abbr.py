#  explain abbr tool
def lambda_handler(event_body,context=None):
    return {"code": 0, "result":event_body['kwargs']['abbr']}
   