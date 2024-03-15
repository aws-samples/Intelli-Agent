import os 
import sys
import threading
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor
sys.path.append("../dep")
from llm_bot_dep import storage_utils

storage_utils.save_content_to_s3 = lambda *args:None 


worker_num = 1
os.environ['aos_injection_chunk_batch_size'] = '50'
os.environ['worker_num'] = str(worker_num)
# os.environ['aos_worker_num'] = str(150)
# os.environ['worker_id'] = str(worker_id)
os.environ['args_path'] = 'user_guide_ingestion.json'
os.environ['AWS_PROFILE'] = 'atl-us-west-2'
os.environ['embedding_endpoint_name'] = 'bge-m3'



def main():
    import local_ingestion_multithread
    local_ingestion_multithread.bge_m3_embedding_lock = threading.Lock()
    local_ingestion_multithread.aos_injection_mp = ProcessPoolExecutor(32)
    print(f'local_ingestion_multithread.aos_injection_mp max worker: {local_ingestion_multithread.aos_injection_mp._max_workers}')
    def run(worker_id):
        local_ingestion_multithread.main(worker_num,worker_id)


    threads = []
    for i in range(worker_num):
        t = threading.Thread(target=run,args=(i,))
        t.daemon = True
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()

