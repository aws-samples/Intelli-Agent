import os
import sys
sys.path.append(".")
import dotenv
dotenv.load_dotenv()
import sys
os.environ['LAMBDA_INVOKE_MODE'] = 'local'

from layer_logic.utils.lambda_invoke_utils import invoke_lambda

def test():
    event_body = {

    }
    r = invoke_lambda(
        lambda_module_path='intention',
        event_body=event_body
        )

    print(r)


if __name__ == "__main__":
    test()