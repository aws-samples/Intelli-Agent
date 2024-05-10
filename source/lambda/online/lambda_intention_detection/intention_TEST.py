from intention import lambda_handler
from utils.lambda_invoke_utils import invoke_with_lambda,invoke_with_handler

def test():
    event_body = {

    }
    r = invoke_with_handler(
        lambda_module_path='intention',
        event_body=event_body
        )

    print(r)


if __name__ == "__main__":
    test()