import json

def lambda_handler(event, context):
    # return 200 directly
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
