def contexts_trunc(docs: list, context_num=2):
        # print('docs len',len(docs))
        docs = [doc for doc in docs[:context_num]]
        # the most related doc will be placed last
        docs.sort(key=lambda x: x.metadata["score"])
        # filter same docs
        s = set()
        context_strs = []
        context_docs = []
        context_sources = []
        for doc in docs:
            content = doc.page_content
            if content not in s:
                context_strs.append(content)
                s.add(content)
                context_docs.append({
                    "doc": content,
                    "source": doc.metadata["source"],
                    "score": doc.metadata["score"]
                    })
                context_sources.append(doc.metadata["source"])
        # print(len(context_docs))
        # print(sg)
        return {
            "contexts": context_strs,
            "context_docs": context_docs,
            "context_sources":context_sources
        }