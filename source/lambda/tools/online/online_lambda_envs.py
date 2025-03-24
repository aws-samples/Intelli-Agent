import boto3
import re

def get_lambda_env_vars(function_name):
    # Initialize a boto3 client for Lambda
    client = boto3.client('lambda')

    # Get the Lambda function configuration
    response = client.get_function_configuration(FunctionName=function_name)

    # Extract environment variables
    env_vars = response.get('Environment', {}).get('Variables', {})

    return env_vars

def generate_env_variable_code_snippet(env_vars):
    # Initialize a list to hold the generated code snippets
    code_snippets = []

    # Loop through each environment variable and generate a code snippet
    for key, value in env_vars.items():
        snippet = f"os.environ['{key}'] = '{value}'"
        code_snippets.append(snippet)

    # Join all the code snippets with newlines
    return "\n".join(code_snippets)


def insert_code_after_imports(file_path, code_snippet):
    # Read the existing Python file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Find the position after the last import statement
    last_import_idx = 0
    for idx, line in enumerate(lines):
        if re.match(r'import os', line):  # Match import statements
            last_import_idx = idx

    # Insert the code snippet after the last import statement
    lines.insert(last_import_idx + 1, '\n' + code_snippet + '\n')

    # Write the modified content back to the file
    with open(file_path, 'w') as file:
        file.writelines(lines)

def format_envs(env_vars):
    return "\n".join(f"{k}={v}" for k,v in env_vars.items())


# Example usage:
if __name__ == "__main__":
    lambda_function_name = "<your_online_main_lambda_function_name>"

    # Get environment variables of the Lambda function
    env_vars = get_lambda_env_vars(lambda_function_name)

    # Generate code snippet
    code_snippet = generate_env_variable_code_snippet(env_vars)
    print(code_snippet)
    
    # # Define the relative path to the Python file where the code should be inserted
    # file_path = "../lambda/online/lambda_main/test/main_local_test_common.py"

    # TODO: Insert the code snippet into the Python file after import statements
    # insert_code_after_imports(file_path, code_snippet)