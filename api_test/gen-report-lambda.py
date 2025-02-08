import json
import boto3
__s3_client = boto3.client('s3') 
def __gen_completed_message(bucket: str, date: str, payload_type: int):
    detail_key=f"{date}_detail_third.json" if payload_type == 0 else f"{date}_detail.json"
    log_key=f"{date}_detail_third.log" if payload_type == 0 else f"{date}_detail.log"
    response = __s3_client.get_object(Bucket=bucket, Key=detail_key)
    log_response = __s3_client.get_object(Bucket=bucket, Key=log_key)
    message = 'BuiltIn KB:\n' if payload_type == 1 else 'Third KB:\n'
    content = log_response['Body'].read().decode('utf-8')
    target_substring = "=================================== FAILURES ==================================="
    end_target_substring = "=============================== warnings summary ==============================="
    substring_index=content.find(target_substring)
    end_substring_index=content.find(end_target_substring)
    print(f"substring_index. =======>{substring_index}")
    start_index=substring_index + len(target_substring)
    if substring_index != -1:
        result_content = content[start_index:end_substring_index]
        print(result_content)
    else:
        result_content = "None"

    json_content = json.loads(response['Body'].read().decode('utf-8'))
    tests_result = json_content['tests']
    passed = 0
    failed = 0
    error = 0
    passed_str="============================= passed ==============================\n"
    failed_str="============================= failed ==============================\n"
    error_str="============================== error  ==============================\n"
    for item in tests_result:
        time = item["setup"]["duration"] + item["teardown"]["duration"]
        if "call" in item:
            time = time + item["setup"]["duration"]
        if item["outcome"] == "passed":
            passed += 1
            passed_str += f"{item['outcome']} - {round(time, 4)} - {item['nodeid']}\n"
        elif item["outcome"] == "failed":
            failed += 1
            failed_str += f"{item['outcome']} - {round(time, 4)} - {item['nodeid']}\n"
        elif item["outcome"] == "error":
            error += 1
            error_str += f"{item['outcome']} - {round(time, 4)} - {item['nodeid']}\n"
        else:
            pass
    passed_str += "\n\n" if passed != 0 else "None\n\n"
    failed_str += "\n\n" if failed != 0 else "None\n\n"
    error_str += "\n\n" if error != 0 else "None\n\n"
    message+= passed_str
    message+= failed_str
    message+= error_str
    message+="\n\n"
    message+="=========================== failures log =============================\n"
    message+=result_content
    message+="\n ...\n\n\n"
    return passed, failed, error, message
    

def __gen_uncompleted_message(payload, payload_type):
    message = 'BuiltIn KB:\n' if payload_type == 1 else 'Third KB:\n'
    message+= "The stack deploy FAILED! The reason for the failure is as follows:"
    message+="\n\n"
    message+=payload['detail']
    message+="\n ..."
    return message
    # __send_report(event['topic'], f"[{event['project_name']}][{datetime.now().strftime('%Y-%m-%d')}][FAILED!] API AutoTest Report", message)

def __send_report(topic, subject, message):
    sns_client = boto3.client('sns')
    sns_client.publish(TopicArn=topic, Subject=subject, Message=message)

def __gen_json_from_s3(bucket: str, date: str, keyword: str, payload_type: int):
    keywords = keyword.split(".")
    key=f"{date}_{keywords[0]}_third.{keywords[1]}" if payload_type == 0 else f"{date}_{keyword}"
    return json.loads(__s3_client.get_object(Bucket=bucket, Key=key)['Body'].read().decode('utf-8'))


def lambda_handler(event, context):
    bucket=event['bucket']
    date = event['date']
    status = "FAILED"
    passed = 0
    failed = 0
    error = 0
    coverage='-'
    third_passed = 0
    third_failed = 0
    third_error = 0
    third_coverage = '-'
    # event={'project_name': 'Chatbot Portal with Agent', 'build_url': 'https://ap-northeast-1.console.aws.amazon.com/codebuild/home?region=ap-northeast-1#/builds/AgentApiTest:9d97a692-cc2c-4372-8538-58a192735f13/view/new', 'status': 'completed', 'bucket': 'intelli-agent-rag-ap-northeast-1-api-test', 's3_key': '2024-06-30_13-21-21_detail.json', 'log': '2024-06-30_13-21-21_detail.log', 'topic': 'arn:aws:sns:ap-northeast-1:544919262599:agent-developers'} 
    # third_payload = __gen_json_from_s3(bucket, date, "payload.json", 0)
    
    payload = __gen_json_from_s3(bucket, date, "payload.json", 1)

    if payload['status'] == 'completed':
        passed, failed, error, msg = __gen_completed_message(bucket, date, 1)
        total=passed + failed + error
        if total != 0:
            coverage = round(passed/total, 2)*100
    else:
        msg = __gen_uncompleted_message(payload, 1)

    # if third_payload['status'] == 'completed':
    #     third_passed, third_failed, third_error, third_msg = __gen_completed_message(bucket, date, 0)
    #     third_total = third_passed + third_failed + third_error
    #     if third_total != 0:
    #         third_coverage = round(third_passed/third_total, 2)*100
    # else:
    #     third_msg = __gen_uncompleted_message(payload, 0)
    # if payload.get('status')=='completed' and third_payload.get('status')=='completed' and failed + error + third_failed + third_error == 0:
    if payload.get('status')=='completed' and failed + error + third_failed + third_error == 0:
        status = "PASSED"
    message = f"Hi, team!\nThe following is API autotest report for {date}.\n\n ============================ summary =============================\n REPOSITORY: {payload['repository']}\n BRANCH: {payload['branch']}\n TEST RESULT: {status}\n Built-In KB:\n     Total:{passed + failed + error}\n     Passed:{passed} Failed:{failed} Error:{error}\n     Coverage:{coverage}%\n Third KB:\n     Total:{third_passed + third_failed + third_error}\n     Passed:{third_passed} Failed:{third_failed} Error:{third_error}\n     Coverage:{third_coverage}%\n\n\n "
    message += msg
    # message += third_msg
    # message+=f"\n\n More details click:\n Built-in KB: {payload['build_url']}\n Third KB: {third_payload['build_url']}"
    message+=f"\n\n More details click:\n Built-in KB: {payload['build_url']}\n"
    message+="\n\nBR.\nThanks"
    
    # Publish to SNS
    __send_report(payload['topic'], f"[{payload['project_name']}][{date}][{status}] API AutoTest Report", message)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
