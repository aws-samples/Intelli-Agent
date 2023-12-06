"""
Note that the ragas version is 0.0.21 in current test
"""

import json 
import pandas as pd 
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import traceback
from tqdm import tqdm
import pickle
import time 
import requests
import os  
from ragas import evaluate
from datasets import Dataset
from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness
)
from ragas.metrics._answer_correctness import answer_correctness

RAGAS_EVAL_METRICS = [answer_correctness,faithfulness]

def load_eval_data(eval_data_path):
    data = pd.read_csv(eval_data_path).to_dict(orient='records')
    ret = []
    for d in data:
        ret.append({
            "question":d['question'],
            "ground_truths": [d['ground truth']]
        })
    return ret 



def csdc_rag_call(
        datum,
        rag_api_url,
        retry_times=3,
        **rag_parameters):
    prompt = datum['question']
    json_data = {
                "model": "knowledge_qa",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **rag_parameters
            }
    retry_time = 1
    while retry_time <= retry_times:
        r = requests.post(
            rag_api_url,
            json=json_data
        )
        if r.status_code == 200:
            ret = r.json()
            answer = ret['choices'][0]['message']['content']
            contexts = [c['content'] for c in json.loads(ret['contexts'])]
            return {
                "question": prompt,
                "contexts": contexts,
                "answer": answer,
                "ground_truths": datum['ground_truths']
            } 
        print(f'retry time: {retry_time}/{retry_times}, meet error: {r.json()}')
        retry_time += 1
        time.sleep(10)

    raise RuntimeError(r.json())
    


def get_rag_result(data,
                   rag_api_url=None,
                   num_worker=1,
                   **rag_parameters
                   ):
    """_summary_

    Args:
        data (_type_): _description_
        rag_api_url (_type_, optional): _description_. Defaults to None.
        num_worker (int, optional): _description_. Defaults to 1.
    """
    futures = []
    ret = []
    with ThreadPoolExecutor(num_worker) as pool:
        for datum in data:
            # question = datum['question']
            future = pool.submit(csdc_rag_call,datum,rag_api_url,**rag_parameters)
            future.datum = datum
            futures.append(future)
        # futures = [pool.submit(Claude2.generate,prompt) for prompt in prompts]
        for future in tqdm(as_completed(futures),total=len(futures)):
            try:
                output_datum = future.result()
            except:
                print(traceback.format_exc())
                output_datum = None
            if output_datum is None:
                datum = future.datum
                datum['answer'] = None 
                ret.append(datum)
                continue
            ret.append(output_datum)
    return ret 

def run_ragas_eval(data,ret_save_profix=''):
    # os.environ["OPENAI_API_KEY"] = openai_api_key
    from ragas import evaluate
    dataset = Dataset.from_pandas(pd.DataFrame(data))
    
    results = evaluate(
        dataset,
        metrics=RAGAS_EVAL_METRICS
        )
    save_path = f'{ret_save_profix}_ragas_eval_res.csv'
    print('saving ragas eval result to : ', save_path)
    results.to_pandas().to_csv(save_path,index=False)
    print('results: ',results)
    return results

def run_eval(
        eval_data_path,
        rag_api_url,
        rag_num_worker=1,
        llm_output_cache_path=None,
        ret_save_profix = '',
        **rag_parameters):
    assert os.getenv('OPENAI_API_KEY'), 'ragas evaluation needs openai api key'
    # load eval_data
    if llm_output_cache_path is not None and \
          os.path.exists(llm_output_cache_path):
        print(f'load cache llm output data: {llm_output_cache_path}')
        with open(llm_output_cache_path,'rb') as f:
            data_to_eval = pickle.load(f)

    else:
        print('loading data......')
        data = load_eval_data(eval_data_path)[:10]
        # get rag result 
        print(f'run rag, {len(data)} example......')
        data_to_eval = get_rag_result(
            data,
            rag_api_url=rag_api_url,
            num_worker=rag_num_worker,
            **rag_parameters
        )
        print(data_to_eval[0])
        if llm_output_cache_path is not None:
            print(f'save llm output to {llm_output_cache_path}')
            with open(llm_output_cache_path,'wb') as f:
                pickle.dump(data_to_eval,f)
             
    # call ragas 
    print(f'run ragas eval, data num: {len(data_to_eval)}')
    ret = run_ragas_eval(data_to_eval,ret_save_profix)
    return ret 


if __name__ == "__main__":
    rag_api_url = "https://5tzaajjzg7.execute-api.us-west-2.amazonaws.com/default/llm-bot-dev-qq-matching"
    eval_data_path = "TechBot QA Test-fifth-test.csv"
    eval_id = 'claude2-csds-retrive'
    llm_output_cache_path = f'{eval_id}-llm-output-cache.pkl'
    ret_save_profix = f'{eval_id}-eval'
   
    rag_parameters = {
        'llm_model_id': "anthropic.claude-v2:1", 
        "temperature": 0.7,
        "enable_q_q_match": True,
        "get_contexts": True
    }
    r = run_eval(
        eval_data_path,
        rag_api_url,
        rag_num_worker=1,
        llm_output_cache_path=llm_output_cache_path,
        ret_save_profix=ret_save_profix,
        **rag_parameters
    )
    print(r)


