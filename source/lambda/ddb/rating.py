import datetime
import json
import boto3
import os
import uuid

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table_name = os.getenv('TABLE_NAME')
    session_table = dynamodb.Table(table_name)

    http_method = event['httpMethod']
    
    try:
        if http_method == 'POST':
            return post_handler(event, session_table)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Invalid request method'
                })
            }
    except Exception as e:
        # Return an error response
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
        
    
def post_handler(event, session_table):
    body = event['body']
    session_id = str(uuid.uuid1())
    required_fields = ['question_content', 'question_answer', 'answer_rating']
    
    if not all(field in body for field in required_fields):
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Missing required fields'
            })
        }
    session_creation_date = datetime.datetime.now().strftime("%m/%d/%y,%H:%M:%S")
    
    # inserting values into table
    response = session_table.put_item(
        Item={
            "session_id":session_id,
            "question_content":body['question_content'],
            "question_answer":body['question_answer'],
            "revised_answer":body['revised_answer'] if 'revised_answer' in body else None,
            "answer_rating":body['answer_rating'],
            
        }
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
        'message': 'Data inserted successfully'
        })
    }