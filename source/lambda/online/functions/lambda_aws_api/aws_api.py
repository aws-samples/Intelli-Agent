def lambda_handler(event, context):
    '''
    event: {
        "body": "{
            \"instance_type\":\"m5.xlarge\",
            \"region\":\"us-east-1\",
            \"term\":\"eserved\",
            \"purchase_option\":\"All Upfront\"
        }"
    }
    '''

    response = {"statusCode": 200, "headers": {"Content-Type": "application/json"}}
    retriever_response = {
        "results": "Region: us-west-2, Price per instance: $10"
    }
    response["body"] = retriever_response

    print(f"finish retriever lambda invoke")
    return response

if __name__ == "__main__":
    print(lambda_handler({}, {}))