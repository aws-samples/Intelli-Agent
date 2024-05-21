import asyncio
import aiohttp
import time
import re
# from bs4 import BeautifulSoup
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from langchain.utilities import GoogleSearchAPIWrapper
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.docstore.document import Document
from langchain.schema.retriever import BaseRetriever
from langchain.agents import Tool

GOOGLE_API_KEY=os.environ.get('GOOGLE_API_KEY',None)
GOOGLE_CSE_ID=os.environ.get('GOOGLE_CSE_ID',None)


class GoogleSearchTool():
    tool:Tool
    topk:int = 5
    
    def __init__(self,top_k=5):  
        self.topk = top_k
        search = GoogleSearchAPIWrapper()
        def top_results(query):
            return search.results(query, self.topk)
        self.tool = Tool(
            name="Google Search Snippets",
            description="Search Google for recent results.",
            func=top_results,
        )
        
    def run(self,query):
        return self.tool.run(query)

def remove_html_tags(text):
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    text = re.sub(r'\r{1,}',"\n\n",text)
    text = re.sub(r'\t{1,}',"\t",text)
    text = re.sub(r'\n{2,}',"\n\n",text)
    return text

async def fetch(session, url, timeout):
    try:
        async with session.get(url) as response:
            return await asyncio.wait_for(response.text(), timeout=timeout)
    except asyncio.TimeoutError:
        print(f"timeout:{url}")
        return ''
    except Exception as e:
        print(f"ClientError:{url}", str(e))
        return ''

    
async def fetch_all(urls, timeout):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            task = asyncio.create_task(fetch(session, url, timeout))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results
    
def web_search(**args):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        logger.info('Missing google API key')
        return []
    tool = GoogleSearchTool(args['top_k'])
    result = tool.run(args['query'])
    # 异常情况返回这个结果[{'Result': 'No good Google Search Result was found'}]
    return [item for item in result if 'title' in item and 'link' in item and 'snippet' in item]

    
def add_webpage_content(snippet_results):
    t1 = time.time()
    urls = [item['doc_author'] for item in snippet_results]
    loop = asyncio.get_event_loop()
    fetch_results = loop.run_until_complete(fetch_all(urls,5))
    t2= time.time()
    logger.info(f'deep web search time:{t2-t1:1f}s')
    final_results = []
    for i, result in enumerate(fetch_results):
        if not result:
            continue
        page_content = remove_html_tags(result)
        final_results.append({**snippet_results[i],
                              'doc':snippet_results[i]['doc']+'\n'+page_content[:10000]
                              })
    return final_results

class GoogleRetriever(BaseRetriever):
    search: Any
    result_num: Any

    def __init__(self, result_num):
        super().__init__()
        self.result_num = result_num

    def _get_relevant_documents(
        self, question: Dict, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        query = question[self.query_key]
        result_list = web_search(query=query, top_k=self.result_num)
        doc_list = []
        for result in result_list:
            doc_list.append(
                Document(
                    page_content=result["doc"],
                    metadata={
                        "source": result["link"],
                        "retrieval_content": result["title"] + '\n' + result["snippet"],
                        "retrieval_data": result["title"]
                    }
                )
            )
        return doc_list

    def get_whole_doc(self, results) -> Dict:
        return add_webpage_content(self._get_relevant_documents(results))