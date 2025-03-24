import os
import boto3


def download_dir_from_s3(bucket_name, s3_dir_path, local_dir_path):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    for result in paginator.paginate(Bucket=bucket_name, Prefix=s3_dir_path):
        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                if not os.path.exists(os.path.dirname(local_dir_path + os.sep + file.get('Key'))):
                    os.makedirs(os.path.dirname(
                        local_dir_path + os.sep + file.get('Key')))
                s3.download_file(bucket_name, file.get('Key'),
                                 local_dir_path + os.sep + file.get('Key'))


def download_file_from_s3(bucket_name, s3_file_path, local_file_path):
    s3 = boto3.client('s3')
    s3.download_file(bucket_name, s3_file_path, local_file_path)


def delete_s3_file(bucket_name, s3_file_path):
    s3 = boto3.client('s3')
    s3.delete_object(Bucket=bucket_name, Key=s3_file_path)


def upload_file_to_s3(bucket_name, s3_file_path, local_file_path):
    s3 = boto3.client('s3')
    s3.upload_file(local_file_path, bucket_name, s3_file_path)


def upload_dir_to_s3(bucket_name, s3_dir_path, local_dir_path):
    for root, dirs, files in os.walk(local_dir_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            s3_file_path = os.path.join(
                s3_dir_path, local_file_path[len(local_dir_path)+1:])
            print(f"Uploading {local_file_path} to {s3_file_path}")
            upload_file_to_s3(bucket_name, s3_file_path, local_file_path)


def check_local_folder(file_path):
    folder = '/'.join(file_path.split('/')[:-1])
    if not os.path.exists(folder):
        os.makedirs(folder)
