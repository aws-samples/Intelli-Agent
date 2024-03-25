## LLM API Invocation Guide

This guide will walk you through the process of invoking the LLM API.

### LLM

#### Question Answering using LLM

To perform question answering using LLM, make a POST request to `https://xxxx.execute-api.us-east-1.amazonaws.com/v1/llm`.

Here is an example of the request body:

```bash
{
    "session_id":"4dd19f1c-45e1-4d18-9d70-7593f96d001a",
    "get_contexts": False,
    "type": "common",
    "messages":[
        {
            "role":"user",
            "content":"question"
        }
    ],
    "retriever_config":{
        "workspace_ids":[
            "your-workspace-id"
        ]
    }
}
```

After making the request, you should see a response similar to this:

```bash
{
    "session_id": "xxx",
    "client_type": "client_type",
    "object": "chat.completion",
    "created": 1709569720,
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "您可以在SSML标记语言中直接嵌入发音,以指定Polly如何朗读密码中的大小写。例如:\n\n<speak>\n<sub alias=\"Capital A\">A</sub>bc123\n</speak>\n\n这会使Polly读出\"大写A bc 一二三\"。您可以为每个字符指定发音。\n\n另外,Polly的语音合成输出可以存储在您自己的系统上,并使用您选择的加密密钥进行加密,以保证安全性。",
                "knowledge_sources": [
                    "https://docs.aws.amazon.com/zh_cn/polly/latest/dg/encryption-at-rest.html",
                    "https://repost.aws/questions/QUjhd0XqSISD-ozlZfQwDedg"
                ]
            },
            "message_id": "ai_message_id",
            "custom_message_id": "custom_message_id",
            "finish_reason": "stop",
            "index": 0
        }
    ],
    "entry_type": "common"
}
```

