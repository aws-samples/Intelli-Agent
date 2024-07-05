import json
from datetime import datetime
import boto3

def __gen_completed_report(event):
    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket="sdps-test-result", Key=event['s3_key'])
    log_response = s3_client.get_object(Bucket="sdps-test-result", Key=event['log'])
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
    
    status = "FAILED!" if (failed + error) > 0 else "PASSED!"
    date_str = datetime.now().strftime('%Y-%m-%d')
    message = f"Hi, team!\nThe following is API autotest report for {date_str}.\n\n ============================ summary =============================\n {status}\n Total:{passed + failed + error} Passed:{passed} Failed:{failed} Error:{error}\n Coverage:61%\n\n\n "
    message+= passed_str
    message+= failed_str
    message+= error_str
    message+="\n\n"
    message+="=========================== failures log =============================\n"
    message+=result_content
    message+="\n ..."
    message+=f"\n\n More details click: {event['build_url']}"
    message+="\n\nBR.\nThanks"
    # Publish to SNS
    __send_report(event['topic'], f"[{event['project_name']}][{date_str}][{status}] API AutoTest Report", message)

def __gen_uncompleted_report(event):
    message = "Hi, team!\nThe stack deployment <span style='color: blue; font-weight: bold;'>failed</span>. The reason for the failure is as follows:"
    message+="\n\n"
    message+=event['detail']
    message+="\n ..."
    message+=f"\n\n More details click: {event['build_url']}"
    message+="\n\nBR.\nThanks"
    __send_report(event['topic'], f"[{event['project_name']}][{datetime.now().strftime('%Y-%m-%d')}][FAILED!] API AutoTest Report", message)

def __send_report(topic, subject, message):
    sns_client = boto3.client('sns')
    sns_client.publish(TopicArn=topic, Subject=subject, Message=message)


def lambda_handler(event,context):
    if event['status'] == 'completed':
        __gen_completed_report(event)
    else:
        __gen_uncompleted_report(event)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
