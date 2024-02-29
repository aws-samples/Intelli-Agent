import json
import boto3
import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(".")
sys.path.append("dep")
sys.path.append("/home/ubuntu/pytorch_gpu_base_ubuntu_uw2_workplace/csdc/llm-bot-env/llm-bot/source/lambda/job/dep")
import ingestion

import multiprocessing as mp
processes = [mp.Process(target=ingestion.main, args=(i,)) for i in range(1)]

# Run processes
for p in processes:
    p.start()

# Exit the completed processes
for p in processes:
    p.join()
