import argparse
import os
from huggingface_hub import snapshot_download

def parse_args():
    parser = argparse.ArgumentParser(description='prepare model for djl serving')
    parser.add_argument('--hf_model_id')
    parser.add_argument("--hf_model_local_dir",help='to save hf model')
    parser.add_argument("--hf_model_revision",default="main",help='to save hf model')
    parser.add_argument("--model_artifact_dir",help='path to model artifacts')
    parser.add_argument("--model_artifact_tar_name",default="model.tar.gz")
    parser.add_argument("--s3_bucket")
    parser.add_argument("--hf_model_s3_prefix")
    parser.add_argument("--model_artifact_s3_prefix")
    return parser.parse_args()

def download_hf_model_to_local(args):
    hf_model_id = args.hf_model_id
    hf_model_local_dir = args.hf_model_local_dir
    hf_model_revision = args.hf_model_revision
    snapshot_download(
        hf_model_id,
        local_dir=hf_model_local_dir,
        local_dir_use_symlinks=False,
        revision=hf_model_revision
    )

def tar_model_artifact(args):
    print(f'tar {args.model_artifact_dir} to {args.model_artifact_tar_name}')
    os.system(f'tar czvf {args.model_artifact_tar_name} {args.model_artifact_dir}')

def push_to_s3(args):
    # push hf model
    print(f'push {args.hf_model_local_dir} to s3://{args.s3_bucket}/{args.hf_model_s3_prefix}')
    os.system(f"aws s3 cp --recursive {args.hf_model_local_dir} s3://{args.s3_bucket}/{args.hf_model_s3_prefix}")
    # push model artifacts
    print(f'push {args.model_artifact_tar_name} to s3://{args.s3_bucket}/{args.model_artifact_s3_prefix}/')
    os.system(f"aws s3 cp {args.model_artifact_tar_name} s3://{args.s3_bucket}/{args.model_artifact_s3_prefix}/")

def main():
    args = parse_args()
    print(f'args: {args}')
    # download hf model to local 
    download_hf_model_to_local(args)
    # tar model artifacts
    tar_model_artifact(args) 
    # push to s3
    push_to_s3(args)
    

if __name__ == "__main__":
    main()



