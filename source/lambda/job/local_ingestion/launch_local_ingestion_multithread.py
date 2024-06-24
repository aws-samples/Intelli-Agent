import itertools
import logging
import multiprocessing
import os
import sys
import threading
import tracemalloc
from multiprocessing import Process, Queue
from typing import Iterable

from langchain_community.vectorstores.opensearch_vector_search import (
    OpenSearchVectorSearch,
)
from opensearchpy import RequestsHttpConnection

sys.path.append("../dep")
from llm_bot_dep import storage_utils

storage_utils.save_content_to_s3 = lambda *args: None
aos_injection_mp_worker_num = 16
aos_injection_batch_size = 50
embedding_chunk_num = 50
os.environ["embedding_chunk_num"] = str(embedding_chunk_num)

logger = logging.getLogger("launch")
logger.setLevel(logging.INFO)


def print_top_stats(process_id, extract_info="", top_k=10):
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics("lineno")
    if process_id > 0:
        return

    s = extract_info + f"process_id: {process_id}. <top_stats>\n"
    top_strs = []
    for stat in top_stats[:top_k]:
        top_strs.append(
            f"{str(top_stats[0].traceback)}, size: {stat.size}, count: {stat.count}"
        )

    s += "\n".join(top_strs)
    s += "\n</top_stats>"
    logger.info(s)


opensearch_obj = None
embedding_size = None


def task_queue_gen(task_queue):
    import local_ingestion_multithread

    global opensearch_obj, embedding_size
    # print(sxfvfg)
    task = task_queue.get()
    if opensearch_obj is None:
        opensearch_obj = OpenSearchVectorSearch(
            index_name=task["index_name"],
            embedding_function=None,
            opensearch_url="https://{}".format(local_ingestion_multithread.aosEndpoint),
            http_auth=local_ingestion_multithread.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )
        embedding_size = len(task["embedding"])
        logger.info(f"embedding size: {embedding_size}")

    yield task
    yield task

    while True:
        task = task_queue.get()
        if task is None:
            return
        yield task


def batch_generator(gen: Iterable, batch_size=aos_injection_batch_size):
    while True:
        if gen.gi_frame is None:
            break
        yield itertools.islice(gen, batch_size)


def process_run(process_id, task_queue):
    logger = logging.getLogger("opensearch")
    logger.setLevel(logging.WARNING)
    import local_ingestion_multithread

    global embedding_size
    gen = batch_generator(task_queue_gen(task_queue))
    should_start = True
    for batch_data in gen:
        if should_start:
            next(batch_data)
            should_start = False

        local_ingestion_multithread.bulk_add(
            opensearch_obj,
            batch_data,
            max_chunk_bytes=1 * 1024 * 1024,
            embedding_size=embedding_size,
        )

    print(f"process: {process_id} finished")


worker_num = 1

os.environ["worker_num"] = str(worker_num)
# os.environ['aos_worker_num'] = str(150)
# os.environ['worker_id'] = str(worker_id)
os.environ["args_path"] = "user_guide_ingestion.json"
os.environ["AWS_PROFILE"] = "atl"
os.environ["embedding_endpoint_name"] = "bge-m3"


def main():
    import local_ingestion_multithread

    local_ingestion_multithread.bge_m3_embedding_lock = threading.Lock()
    local_ingestion_multithread.index_create_lock = multiprocessing.Lock()

    # local_ingestion_multithread.aos_injection_mp = ProcessPoolExecutor(aos_injection_mp_worker_num)
    # start all process
    # for _ in range(aos_injection_mp_worker_num):
    #     local_ingestion_multithread.aos_injection_mp.submit(lambda x:None)
    task_queue = Queue(maxsize=1)
    local_ingestion_multithread.aos_injection_task_queue = task_queue
    processes = []
    for index in range(aos_injection_mp_worker_num):
        p = Process(target=process_run, args=(index, task_queue))
        p.daemon = True
        processes.append(p)

    for p in processes:
        p.start()

    # print(f'local_ingestion_multithread.aos_injection_mp max worker: {local_ingestion_multithread.aos_injection_mp._max_workers}')
    print(
        f"local_ingestion_multithread.aos_injection_mp max worker: {aos_injection_mp_worker_num}"
    )

    local_ingestion_multithread.main(worker_num, 0)

    for _ in processes:
        task_queue.put(None)

    for p in processes:
        p.join()

    print("finished")


if __name__ == "__main__":
    main()
