import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3

sys.path.append(".")
sys.path.append("dep")
sys.path.append(
    "/home/ubuntu/pytorch_gpu_base_ubuntu_uw2_workplace/csdc/llm-bot-env/llm-bot/source/lambda/job/dep"
)
import multiprocessing as mp

import ingestion

processes = [mp.Process(target=ingestion.main, args=(i,)) for i in range(1)]

# Run processes
for p in processes:
    p.start()

# Exit the completed processes
for p in processes:
    p.join()
