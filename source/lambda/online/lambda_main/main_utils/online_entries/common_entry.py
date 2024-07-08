import json
from typing import Annotated, Any, TypedDict

from common_logic.common_utils.constant import LLMTaskType,ChatbotMode,MessageType
from common_logic.common_utils.exceptions import (
    ToolNotExistError, 
    ToolParameterNotExistError,
    MultipleToolNameError,
    ToolNotFound
)
from common_logic.common_utils.time_utils import get_china_now
from common_logic.common_utils.lambda_invoke_utils import (
    invoke_lambda,
    is_running_local,
    node_monitor_wrapper,
    send_trace,
)
from common_logic.common_utils.python_utils import add_messages, update_nest_dict
from common_logic.common_utils.logger_utils import get_logger
from common_logic.common_utils.prompt_utils import get_prompt_templates_from_ddb
from common_logic.common_utils.serialization_utils import JSONEncoder
from functions.tool_calling_parse import parse_tool_calling as _parse_tool_calling
from functions.tool_execute_result_format import format_tool_call_results
from functions.tools import Tool, get_tool_by_name, tool_manager
from lambda_main.main_utils.parse_config import parse_common_entry_config
from langgraph.graph import END, StateGraph


logger = get_logger('common_entry')

intention_fewshot_default = [
    {
        "query": "早上好，你好吗?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你好",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你好吗?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你听到新闻了吗?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你最喜欢什么书?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你是谁?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "我在做个东西.",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "蛋糕是一个谎言.",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "复杂优于晦涩.",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你是一个程序员吗?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "YOLO是什么意思?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "我从未活过吗?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "我能问你一个问题吗?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你喜欢什么食物?",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你的爱好是什么？",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "我告诉你一个秘密，你不要和别人说",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "什么是爱",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "你爱我吗？",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "中国首都是哪？",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "今天心情有点糟",
        "score": 0.9,
        "name": "chat",
        "intent": "chat",
        "kwargs": {}
    },
    {
        "query": "中国区有没有glue interactive session?",
        "score": 0.9,
        "name": "service_availability",
        "intent": "service_availability",
        "kwargs": {"service": "glue interactive session", "region": "cn-north-1"}
    },
    {
        "query": "北京region 有没有clean room服务？",
        "score": 0.9,
        "name": "service_availability",
        "intent": "service_availability",
        "kwargs": {"service": "clean room", "region": "cn-north-1"}
    },
    {
        "query": "zero-etl在中国可用了吗？",
        "score": 0.9,
        "name": "service_availability",
        "intent": "service_availability",
        "kwargs": {"service": "zero-etl", "region": "cn-north-1"}
    },
    {
        "query": "中国区sagemaker有jumpstart吗",
        "score": 0.9,
        "name": "service_availability",
        "intent": "service_availability",
        "kwargs": {"service": "jumpstart", "region": "cn-north-1"}
    },
    {
        "query": "quicksight在中国区可用吗？",
        "score": 0.9,
        "name": "service_availability",
        "intent": "service_availability",
        "kwargs": {"service": "quicksight", "region": "cn-north-1"}
    },
    {
        "query": "quicksight在伦敦region可用吗？",
        "score": 0.9,
        "name": "service_availability",
        "intent": "service_availability",
        "kwargs": {"service": "quicksight", "region": "eu-west-2"}
    },
    {
        "query": "DataZone在global region GA了吗？",
        "score": 0.9,
        "name": "service_availability",
        "intent": "service_availability",
        "kwargs": {"service": "DataZone", "region": "us-east-1"}
    },
    {
        "query": "你们的服务烂透了",
        "score": 0.9,
        "name": "comfort",
        "intent": "comfort",
        "kwargs": {}
    },
    {
        "query": "你这个系统弱智啊",
        "score": 0.9,
        "name": "comfort",
        "intent": "comfort",
        "kwargs": {}
    },
    {
        "query": "到底行不行，不行别浪费时间",
        "score": 0.9,
        "name": "comfort",
        "intent": "comfort",
        "kwargs": {}
    },
    {
        "query": "无语了，没见过这么垃圾的玩意",
        "score": 0.9,
        "name": "comfort",
        "intent": "comfort",
        "kwargs": {}
    },
    {
        "query": "回复的什么乱七八糟的",
        "score": 0.9,
        "name": "comfort",
        "intent": "comfort",
        "kwargs": {}
    },
    {
        "query": "傻逼",
        "score": 0.9,
        "name": "comfort",
        "intent": "comfort",
        "kwargs": {}
    },
    {
        "query": "中国区有哪些大模型可以推荐",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "gloabl有哪些大模型可以推荐",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "什么是 AWS Organizations？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "如何从组织删除 AWS 成员账户？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "一个 AWS 账户可以是多个 OU 的成员吗？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "Amazon Rekognition 支持哪些图像和视频格式？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "Network Load Balancer 是否支持内部负载均衡器？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "对于创建堆栈失败期间回滚的资源，我是否需要付费？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "Amazon SQS 符合 HIPAA 要求吗？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "如何共享消息队列？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "Amazon EMR有哪些优势",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "FOOB Ticket 的链接是什么",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "怎么提交FOOB？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "怎么申请p4d p5?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "P5的spot limit应该怎么提？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "宁夏区的GPU资源的情况？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "inferentia2/traninium1中国区landing plan？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "GPU OD的价格基础上如何可以有进一步的折扣？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "需要提前多久申请FOOB？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "申请GPU实例的FOOB 链接是什么？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "ODCR预留实例怎么计费？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "怎么看资源分配是否有risk？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "What is \"Unoccupied hosts\" in baywatch",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "what is Free slots in baywatch?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "How do I know if the instance type is GA or not GA?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "what is FOOB?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "what are the use cases for FOOB?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "in what senarios, I need FOOB?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "what if the customer has EBS requirement",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "请用中文回答 what if the customer has EBS requirement",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "what are the differences between Incremental Capacity Request ICR ticket and Limit increase (Service Quota) request?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "how to request for p4d, p5",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "what is the approval template for requesting p4d?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "ODCR预留怎么计费？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "ODCR怎么享受RI 或者Savings Plan计费？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "what is baywatch?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "怎么看现有的Capacity？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "申请gpu foob的流程是什么？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "OCI的资料有哪些？",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "什么是生成式AI?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "什么是Gen-AI?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "SageMaker Feature Store 与 Azure 托管功能商店有什么不同?",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "Sagemaker如何使用张量并行技术对模型分层",
        "score": 0.9,
        "name": "QA",
        "intent": "QA",
        "kwargs": {}
    },
    {
        "query": "翻译：在中国背景下，创业意向影响因素可划分为两层次(个体特质水平和个体资源水平)六维度(成就动机，风险承担，自主性，创业回馈，资源获得和未来就业)",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "你是一个英语学术论文写作专家，以下是一篇论文中的一段内容，请先对齐进行翻译，并将此部分润色以满足学术标准，提高语法,清晰度和整体可读性",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "帮我写一段工作小结，以下是我的一些工作内容:...",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "帮我写一个PPT大纲，用于年中汇报",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "翻译成中文：Bought In Team",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "改写得更简练，但是要适合口述演讲，不能机械化",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "翻译：场景化解决方案的最佳实践大力促进了genai在类似客户里的推广",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "revise to be more readable",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "把下面的readme翻译成英文：本项目为一个基于Amazon Bedrock，Amazon SageMaker，Amazon RDS和Amazon Opensearch实现的轻量级的Text2SQL Agent的Workshop：包括Plan-and-Execute Agent和ReAct两种不同的实现。",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "translate into english: lxq_voc_gen.csv是option1需要用到的数据，lxq_cm_gen_raw.csv是option2需要用到的数据",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "pydantic 中文意思",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "给我一段脚本，实现连接mysql数据库",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "英文怎么说：中文大语言模型",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "summarize into one",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "refine below documentation to be more formal",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "帮我写一段适用于sdxl生成图片的prompt，要求效果好",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "帮我写一段适用于sdxl生成“运动会”图片的prompt，要求效果好，用英文",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "帮我把下面的文本整理成markdown格式",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "竞品 英文",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "代码生成 英文",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "错误归因 英文",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "请翻译成中文",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "please translate to chinese",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "请翻译",
        "score": 0.9,
        "name": "assist",
        "intent": "assist",
        "kwargs": {}
    },
    {
        "query": "MDU啥意思",
        "score": 0.9,
        "name": "explain_abbr",
        "intent": "explain_abbr",
        "kwargs": {"abbr": "MDU"}
    },
    {
        "query": "YOY什么意思",
        "score": 0.9,
        "name": "explain_abbr",
        "intent": "explain_abbr",
        "kwargs": {"abbr": "YOY"}
    },
    {
        "query": "CSDC是啥？",
        "score": 0.9,
        "name": "explain_abbr",
        "intent": "explain_abbr",
        "kwargs": {"abbr": "CSDC"}
    },
    {
        "query": "WWSO",
        "score": 0.9,
        "name": "explain_abbr",
        "intent": "explain_abbr",
        "kwargs": {"abbr": "WWSO"}
    },
    {
        "query": "CSDC",
        "score": 0.9,
        "name": "explain_abbr",
        "intent": "explain_abbr",
        "kwargs": {"abbr": "CSDC"}
    },
    {
        "query": "缩写OP2",
        "score": 0.9,
        "name": "explain_abbr",
        "intent": "explain_abbr",
        "kwargs": {"abbr": "OP2"}
    },
    {
        "query": "Bruce负责哪一块？",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"employee": "Bruce"}
    },
    {
        "query": "Lily 负责哪一部份？？",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"employee": "Lily"}
    },
    {
        "query": "请问Lex是哪位SSA老师负责啊？有个api的问题请教一下",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"role": "Tech", "scope": "Lex"}
    },
    {
        "query": "quicksight的GTMS是谁",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"role": "Product Manager", "scope": "quicksight"}
    },
    {
        "query": "quicksight的产品经理是谁？",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"role": "Product Manager", "scope": "quicksight"}
    },
    {
        "query": "数据治理的GTMS是谁？",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"role": "Product Manager", "scope": "Analytics"}
    },
    {
        "query": "AIML北区的Sales是谁？",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"role": "Sales", "domain": "AIML", "scope": "north"}
    },
    {
        "query": "AIML北区的BD是谁？",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"role": "Sales", "domain": "AIML", "scope": "north"}
    },
    {
        "query": "Sagemaker相关问题应该联系谁？",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"scope": "SageMaker"}
    },
    {
        "query": "Emr相关问题应该联系谁？",
        "score": 0.9,
        "name": "get_contact",
        "intent": "get_contact",
        "kwargs": {"scope": "EMR"}
    },
    {
        "query": "g4dn的价格是多少",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "g4dn"}
    },
    {
        "query": "g4dn在美西2的价格？",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "g4dn", "region": "us-west-2"}
    },
    {
        "query": "p4d的价格是多少",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "p4d"}
    },
    {
        "query": "p4d在宁夏的价格？",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "p4d", "region": "cn-northwest-1"}
    },
    {
        "query": "c5.large的价格是多少",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "c5.large"}
    },
    {
        "query": "c5.large在东京的价格？",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "c5.large", "region": "ap-northeast-1"}
    },
    {
        "query": "t3.micro的价格是多少",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "t3.micro"}
    },
    {
        "query": "t3.micro在弗吉尼亚北部的价格？",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "t3.micro", "region": "us-east-1"}
    },
    {
        "query": "m5.xlarge的价格是多少",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "m5.xlarge"}
    },
    {
        "query": "m5.xlarge在悉尼的价格？",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "m5.xlarge", "region": "ap-southeast-2"}
    },
    {
        "query": "r5.2xlarge的价格是多少",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "r5.2xlarge"}
    },
    {
        "query": "r5.2xlarge在法兰克福的价格？",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "r5.2xlarge", "region": "eu-central-1"}
    },
    {
        "query": "i3.metal的价格是多少",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "i3.metal"}
    },
    {
        "query": "i3.metal在圣保罗的价格？",
        "score": 0.9,
        "name": "ec2_price",
        "intent": "ec2_price",
        "kwargs": {"instance_type": "i3.metal", "region": "sa-east-1"}
    }
]

class ChatbotState(TypedDict):
    chatbot_config: dict  # chatbot config
    query: str
    ws_connection_id: str
    stream: bool
    query_rewrite: str = None  # query rewrite ret
    intent_type: str = None  # intent
    intention_fewshot_examples: list
    trace_infos: Annotated[list[str], add_messages]
    message_id: str = None
    chat_history: Annotated[list[dict], add_messages]
    agent_chat_history: Annotated[list[dict], add_messages]
    debug_infos: Annotated[dict, update_nest_dict]
    answer: Any  # final answer
    current_monitor_infos: str
    extra_response: Annotated[dict, update_nest_dict]
    contexts: str = None
    all_index_retriever_contexts: list
    current_agent_tools_def: list[dict]
    current_agent_model_id: str
    current_agent_output: dict
    parse_tool_calling_ok: bool
    enable_trace: bool
    format_intention: str
    ########### function calling parameters ###########
    # 
    current_function_calls: list[str]
    current_tool_execute_res: dict
    current_intent_tools: list
    current_tool_calls: list
    current_tool_name: str
    valid_tool_calling_names: list[str]
    # parameters to monitor the running of agent
    agent_recursion_limit: int # the maximum number that tool_plan_and_results_generation node can be called
    agent_recursion_validation: bool
    current_agent_recursion_num: int #
    

def get_common_system_prompt():
    now = get_china_now()
    date_str = now.strftime("%Y年%m月%d日")
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday = weekdays[now.weekday()]
    system_prompt = f"你是一个亚马逊云科技的AI助理，你的名字是亚麻小Q。今天是{date_str},{weekday}. "
    return system_prompt

####################
# nodes in lambdas #
####################


@node_monitor_wrapper
def query_preprocess_lambda(state: ChatbotState):
    output: str = invoke_lambda(
        event_body=state,
        lambda_name="Online_Query_Preprocess",
        lambda_module_path="lambda_query_preprocess.query_preprocess",
        handler_name="lambda_handler",
    )
    send_trace(f"\n\n**query_rewrite:** \n{output}", state["stream"], state["ws_connection_id"], state["enable_trace"])
    return {"query_rewrite": output}


@node_monitor_wrapper
def intention_detection_lambda(state: ChatbotState):
    intention_fewshot_examples = invoke_lambda(
        lambda_module_path="lambda_intention_detection.intention",
        lambda_name="Online_Intention_Detection",
        handler_name="lambda_handler",
        event_body=state,
    )
    
    # Tools will be empty and will redirect to LLM implicitly by default
    current_intent_tools: list[str] = list(
        set([e["intent"] for e in intention_fewshot_examples])
    )
    # default intention_fewshot_examples using context in built-in bucket
    use_default = False
    if not intention_fewshot_examples:
        use_default = True
        intention_fewshot_examples = intention_fewshot_default
        # use assist and give_rhetorical_question as default
        current_intent_tools = ["assist", "give_rhetorical_question"]

    # send trace
    send_trace(
        f"**intention retrieved (use default: {use_default}):**\n{json.dumps(intention_fewshot_examples,ensure_ascii=False,indent=2)}", 
        state["stream"], 
        state["ws_connection_id"], 
        state["enable_trace"]
    )

    return {
        "intention_fewshot_examples": intention_fewshot_examples,
        "current_intent_tools": current_intent_tools,
        "intent_type": "intention detected",
    }



# @node_monitor_wrapper
# def rag_all_index_lambda(state: ChatbotState):
#     # call retrivever
#     retriever_params = state["chatbot_config"]["all_index_retriever_config"]
#     retriever_params["query"] = state["query"]
#     output: str = invoke_lambda(
#         event_body=retriever_params,
#         lambda_name="Online_Function_Retriever",
#         lambda_module_path="functions.lambda_retriever.retriever",
#         handler_name="lambda_handler",
#     )
#     contexts = [doc["page_content"] for doc in output["result"]["docs"]]
#     send_trace("**all index retriever lambda result** \n" + ("\n"+"="*50 + "\n").join(contexts))
#     return {"all_index_retriever_contexts": contexts}

@node_monitor_wrapper
def rag_llm_lambda(state: ChatbotState):
    group_name = state['chatbot_config']['group_name']
    llm_config = state["chatbot_config"]["rag_config"]["llm_config"]
    task_type = LLMTaskType.RAG
    prompt_templates_from_ddb = get_prompt_templates_from_ddb(
        group_name,
        model_id = llm_config['model_id'],
    )

    output: str = invoke_lambda(
        lambda_name="Online_LLM_Generate",
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name="lambda_handler",
        event_body={
            "llm_config": {
                **prompt_templates_from_ddb,
                **llm_config,
                "stream": state["stream"],
                "intent_type": task_type,
            },
            "llm_input": {
                "contexts": [state["contexts"]],
                "query": state["query"],
                "chat_history": state["chat_history"],
            },
        },
    )
    return {"answer": output}


@node_monitor_wrapper
def agent_lambda(state: ChatbotState):
    # system_prompt = get_common_system_prompt()
    # all_index_retriever_contexts = state.get("all_index_retriever_contexts",[])
    # all_index_retriever_contexts = state.get("contexts",[])
    # if all_index_retriever_contexts:
    #     context = '\n\n'.join(all_index_retriever_contexts)
    #     system_prompt += f"\n下面有一些背景信息供参考:\n<context>\n{context}\n</context>\n"
    # judge recent tool calling type, if it's 
    # if retriever_tool_check(state):
        
    #     contexts = [doc["page_content"] for doc in output["result"]["docs"]]
    #     state["contexts"] = contexts

    current_agent_output:dict = invoke_lambda(
        event_body={
            **state,
            "other_chain_kwargs": {"system_prompt": get_common_system_prompt()}
            },
        lambda_name="Online_Agent",
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler",
   
    )
    current_agent_recursion_num = state['current_agent_recursion_num'] + 1
    send_trace(f"\n\n**current_agent_output:** \n{json.dumps(current_agent_output['agent_output'],ensure_ascii=False,indent=2)}\n\n **current_agent_recursion_num:** {current_agent_recursion_num}", state["stream"], state["ws_connection_id"])
    return {
        "current_agent_output": current_agent_output,
        "current_agent_recursion_num": current_agent_recursion_num
    }


@node_monitor_wrapper
def parse_tool_calling(state: ChatbotState):
    """executor lambda
    Args:
        state (NestUpdateState): _description_

    Returns:
        _type_: _description_
    """
    # parse tool_calls:
    try:
        output = _parse_tool_calling(
            agent_output=state['current_agent_output']
        )
        tool_calls = output['tool_calls']
        send_trace(f"\n\n**tool_calls parsed:** \n{tool_calls}", state["stream"], state["ws_connection_id"], state["enable_trace"])
        if not state["extra_response"].get("current_agent_intent_type", None):
            state["extra_response"]["current_agent_intent_type"] = output['tool_calls'][0]["name"]
       
        return {
            "parse_tool_calling_ok": True,
            "current_tool_calls": tool_calls,
            "agent_chat_history": [output['agent_message']]
        }
    
    except (ToolNotExistError,
             ToolParameterNotExistError,
             MultipleToolNameError,
             ToolNotFound
             ) as e:
        send_trace(f"\n\n**tool_calls parse failed:** \n{str(e)}", state["stream"], state["ws_connection_id"], state["enable_trace"])
        return {
            "parse_tool_calling_ok": False,
            "agent_chat_history":[
                e.agent_message,
                e.error_message
            ]
        }


@node_monitor_wrapper
def agent(state: ChatbotState):
    response = app_agent.invoke(state)
    return response


@node_monitor_wrapper
def tool_execute_lambda(state: ChatbotState):
    """executor lambda
    Args:
        state (NestUpdateState): _description_

    Returns:
        _type_: _description_
    """
    tool_calls = state['current_tool_calls']
    assert len(tool_calls) == 1, tool_calls
    tool_call_results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_kwargs = tool_call['kwargs']
        # call tool
        output = invoke_lambda(
            event_body = {
                "tool_name":tool_name,
                "state":state,
                "kwargs":tool_kwargs
                },
            lambda_name="Online_Tool_Execute",
            lambda_module_path="functions.lambda_tool",
            handler_name="lambda_handler"   
        )
        tool_call_results.append({
            "name": tool_name,
            "output": output,
            "kwargs": tool_call['kwargs'],
            "model_id": tool_call['model_id']
        })
    
    output = format_tool_call_results(tool_calls[0]['model_id'],tool_call_results)
    send_trace(f'**tool_execute_res:** \n{output["tool_message"]["content"]}')
    return {"agent_chat_history": [output['tool_message']]}


@node_monitor_wrapper
def rag_all_index_lambda(state: ChatbotState):
    # call retrivever
    retriever_params = state["chatbot_config"]["rag_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler",
    )
    contexts = [doc["page_content"] for doc in output["result"]["docs"]]
    return {"contexts": contexts}

@node_monitor_wrapper
def aws_qa_lambda(state: ChatbotState):
    # call retrivever
    retriever_params = state["chatbot_config"]["aws_qa_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler",
    )
    contexts = [doc["page_content"] for doc in output["result"]["docs"]]
    return {"contexts": contexts}


@node_monitor_wrapper
def chat_llm_generate_lambda(state: ChatbotState):
    group_name = state['chatbot_config']['group_name']
    llm_config = state["chatbot_config"]["chat_config"]
    task_type = LLMTaskType.CHAT

    prompt_templates_from_ddb = get_prompt_templates_from_ddb(
        group_name,
        model_id = llm_config['model_id'],
    )
    logger.info(prompt_templates_from_ddb)

    answer: dict = invoke_lambda(
        event_body={
            "llm_config": {
                **llm_config,
                "stream": state["stream"],
                "intent_type": task_type,
                "system_prompt": get_common_system_prompt(),
                **prompt_templates_from_ddb
            },
            "llm_input": {
                "query": state["query"],
                "chat_history": state["chat_history"],
               
            },
        },
        lambda_name="Online_LLM_Generate",
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name="lambda_handler",
    )
    return {"answer": answer}


def format_reply(state: ChatbotState):
    recent_tool_name = state["current_tool_calls"][0]['name']
    if recent_tool_name == 'comfort':
        return {"answer": "不好意思没能帮到您，是否帮你转人工客服？"}
    if recent_tool_name == 'transfer':
        return {"answer": "立即为您转人工客服，请稍后"}

def give_rhetorical_question(state: ChatbotState):
    recent_tool_calling: list[dict] = state["current_tool_calls"][0]
    return {"answer": recent_tool_calling["kwargs"]["question"]}


def give_final_response(state: ChatbotState):
    recent_tool_calling: list[dict] = state["current_tool_calls"][0]
    # give_rhetorical_question
    if "question" in recent_tool_calling["kwargs"].keys():
        answer = recent_tool_calling["kwargs"]["question"]
    elif "response" in recent_tool_calling["kwargs"].keys():
        answer = recent_tool_calling["kwargs"]["response"]
    elif "abbr" in recent_tool_calling["kwargs"].keys():
        answer = recent_tool_calling["kwargs"]["abbr"]
    else:
        answer = format_reply(state)["answer"]
    return {"answer": answer}


def qq_matched_reply(state: ChatbotState):
    return {"answer": state["answer"]}


################
# define edges #
################

def query_route(state: dict):
    return f"{state['chatbot_config']['chatbot_mode']} mode"


def intent_route(state: dict):
    if not state['intention_fewshot_examples']:
        state['extra_response']['current_agent_intent_type'] = 'final_rag'
        return 'no clear intention'
    return state["intent_type"]

# def agent_route(state: dict):
#     if state["agent_state"] == "tool calling":
#         return "tool calling"
#     else:
#         return "no need tool calling"

def agent_route(state: dict):
    state["agent_recursion_validation"] = state['current_agent_recursion_num'] < state['agent_recursion_limit']
    if state["parse_tool_calling_ok"]:
        state["current_tool_name"] = state["current_tool_calls"][0]["name"]
    else:
        state["current_tool_name"] = ""

    # if state["agent_recursion_validation"] and not state["parse_tool_calling_ok"]:
    #     return "invalid tool calling"
    if state["agent_recursion_validation"]:
        if state["current_tool_name"] in ["QA", "service_availability", "explain_abbr"]:
            return "force to retrieve all knowledge"
        elif state["current_tool_name"] in state["valid_tool_calling_names"]:
            return "valid tool calling"
        else:
            return "no need tool calling"
    else:
        return "force to retrieve all knowledge"

    # # if recent_tool_name in ["assist", "chat"]:
    # if state["agent_recursion_validation"] and state["current_tool_name"] in state["valid_tool_calling_names"]:
    #     return "valid tool calling"
    # else:
    #     return "no need tool calling"

    # # invalid tool calling
    # if not parse_tool_calling_ok:
    #     if state['current_agent_recursion_num'] >= state['agent_recursion_limit']:
    #         send_trace(f"Reach the agent recursion limit: {state['agent_recursion_limit']}, route to final rag")
    #         return 'first final response/rag intention/recursion limit'
    #     return "invalid tool calling"

    # recent_tool_calls: list[dict] = state["current_tool_calls"]

    # if not recent_tool_calls:
    #     return "no tool"

    # recent_tool_call = recent_tool_calls[0]

    # recent_tool_name = recent_tool_call["name"]

    # if recent_tool_name in ["comfort", "transfer"]:
    #     return "no need tool calling"
    #     # return "format reply"

    # if recent_tool_name in ["QA", "service_availability", "explain_abbr"]:
    #     return "no need tool calling"
    #     # return "aws qa"

    # if recent_tool_name in ["assist", "chat"]:
    #     return "no need tool calling"
    #     # return "chat"

    # if recent_tool_call["name"] == "give_rhetorical_question":
    #     return "no need tool calling"
    #     # return "rhetorical question"

    # if recent_tool_call["name"] == "give_final_response":
    #     if state['current_agent_recursion_num'] == 1:
    #         return "no need tool calling"
    #         # return "force to retrieve all knowledge"
    #         # return "first final response/rag intention/recursion limit"
    #     else:
    #         return "no need tool calling"
    #         # return "generate results"
    #         # return "give final response"
    
    # if state['current_agent_recursion_num'] >= state['agent_recursion_limit']:
    #     send_trace(f"Reach the agent recursion limit: {state['agent_recursion_limit']}, route to final rag")
    #     return "no need tool calling"
    #     # return "force to retrieve all knowledge"

    # return "valid tool calling"
    # # return "continue"

def rag_all_index_lambda_route(state: dict):
    if state['chatbot_config']['chatbot_mode'] == ChatbotMode.rag_mode:
        return "generate results in rag mode"

    if not state.get('intention_fewshot_examples',[]) and state['current_agent_recursion_num'] == 0:
        return "no clear intention"
    else:
        return "generate results in rag mode"

#############################
# define online top-level graph #
#############################

def build_graph():
    workflow = StateGraph(ChatbotState)
    # add all nodes
    workflow.add_node("query_preprocess", query_preprocess_lambda)
    # chat mode
    workflow.add_node("llm_direct_results_generation", chat_llm_generate_lambda)
    # rag mode
    workflow.add_node("all_knowledge_retrieve", rag_all_index_lambda)
    workflow.add_node("llm_rag_results_generation", rag_llm_lambda)
    # agent mode
    workflow.add_node("intention_detection", intention_detection_lambda)
    workflow.add_node("matched_query_return", qq_matched_reply)
    # workflow.add_node("tools_choose_and_results_generation", agent_lambda)
    workflow.add_node("agent", agent)
    workflow.add_node("tools_execution", tool_execute_lambda)
    # workflow.add_node("results_evaluation", parse_tool_calling)
    workflow.add_node("final_results_preparation", give_final_response)
    # workflow.add_node("format_reply", format_reply)
    # workflow.add_node("comfort_reply", comfort_reply)
    # workflow.add_node("transfer_reply", transfer_reply)
    # workflow.add_node("give_rhetorical_question", give_rhetorical_question)
    # workflow.add_node("give_response_wo_tool", give_response_without_any_tool)
    # workflow.add_node("rag_all_index_lambda", rag_all_index_lambda)
    # workflow.add_node("aws_qa_lambda", aws_qa_lambda)
    # workflow.add_node("rag_generate_output", rag_llm_lambda)
    # workflow.add_node("agent_evaluation", parse_tool_calling)

    # add all edges
    workflow.set_entry_point("query_preprocess")
    # chat mode
    workflow.add_edge("llm_direct_results_generation", END)
    # rag mode
    # workflow.add_edge("all_knowledge_retrieve", "llm_rag_results_generation")
    workflow.add_edge("llm_rag_results_generation", END)
    # agent mode
    # workflow.add_edge("tools_choose_and_results_generation", "results_evaluation")
    workflow.add_edge("tools_execution", "agent")
    workflow.add_edge("matched_query_return", "final_results_preparation")
    workflow.add_edge("final_results_preparation", END)
    # workflow.add_edge("rag_all_index_lambda", "rag_llm_lambda")
    # workflow.add_edge("aws_qa_lambda", "rag_llm_lambda")
    # workflow.add_edge("rag_llm_lambda", END)
    # workflow.add_edge("format_reply", END)
    # workflow.add_edge("comfort_reply", END)
    # workflow.add_edge("transfer_reply", END)
    # workflow.add_edge("give_rhetorical_question", END)
    # workflow.add_edge("give_final_response", END)
    # workflow.add_edge("give_response_wo_tool", END)
    # workflow.add_edge("rag_all_index_lambda", "rag_llm_lambda")
    # workflow.add_edge("rag_llm_lambda", END)

    # add conditional edges
    # choose running mode based on user selection:
    # 1. chat mode: let llm generate results directly
    # 2. rag mode: retrive all knowledge and let llm generate results
    # 3. agent mode: let llm generate results based on intention detection, tool calling and retrieved knowledge
    workflow.add_conditional_edges(
        "query_preprocess",
        query_route,
        {
            "chat mode": "llm_direct_results_generation",
            "rag mode": "all_knowledge_retrieve",
            "agent mode": "intention_detection",
        },
    )

    # three running branch will be chosen based on intention detection results:
    # 1. query matched: if very similar queries were found in knowledge base, these queries will be given as results
    # 2. no clear intentions: if no clear intention detected, all knowledge will be retrieved and let llm give the answer based on retrieved results (rag mode)
    # 3. intention detected: if intention detected, the agent logic will be invoked
    workflow.add_conditional_edges(
        "intention_detection",
        intent_route,
        {
            "similar query found": "matched_query_return",
            "intention detected": "agent",
            "no clear intention": "all_knowledge_retrieve", 
        },
    )

    # the results of agent planning will be evaluated and decide next step:
    # 1. invalid tool calling: if agent makes clear mistakes, like wrong tool names or format, it will be forced to plan again
    # 2. valid tool calling: the agent chooses the valid tools
    # 3. generate results: based on running of tools, agent thinks it's ok to generate results.
    # 4. force retrieve all knowledge and generate results: to address hallucination and stability issues, we force agent to retrieve all knowledge and generate results:
    # 4.1 the agent believes that it can produce results without executing tools
    # 4.2 the tools_choose_and_results_generation node reaches its maximum recusion limit
    workflow.add_conditional_edges(
        "agent",
        agent_route,
        {
            # "invalid tool calling": "tools_choose_and_results_generation",
            "valid tool calling": "tools_execution",
            "no need tool calling": "final_results_preparation",
            "force to retrieve all knowledge": "all_knowledge_retrieve", 
            # "give final response": "give_final_response",
            # "rhetorical question": "give_rhetorical_question",
            # "format reply": "format_reply",
            # "comfort": "comfort_reply",
            # "transfer": "transfer_reply",
            # "chat": "chat_llm_generate_lambda",
            # "aws qa": "aws_qa_lambda",
            # "continue": "tool_execute_lambda",
            # "first final response/rag intention/recursion limit": "rag_all_index_lambda",
        },
    )

    # when all knowledge retrieved, there are two possible next steps:
    # 1. no clear intention: this happens when no clear intention (no few shots) is detected, we give agent enough context to think and plan.
    # 2. generate results in rag mode: let llm generate results based on retrieved knowledge, this happens in the following scenarios:
    # 2.1 in rag mode based on user selection at beginning
    # 2.2 agent thinks it needs to retrieve all the knowledge to generate the results
    # 2.3 the agent believes that it can produce results without executing tools
    # 2.4 the tools_choose_and_results_generation node reaches its maximum recusion limit
    workflow.add_conditional_edges(
        "all_knowledge_retrieve",
        rag_all_index_lambda_route,
        {
            "no clear intention": "agent",
            "generate results in rag mode": "llm_rag_results_generation",
        },
    )
    app = workflow.compile()
    return app

#############################
# define online agent graph #
#############################

def build_agent_graph():
    def _results_evaluation_route(state: dict):
        #TODO: pass no need tool calling or valid tool calling?
        state["agent_recursion_validation"] = state['current_agent_recursion_num'] < state['agent_recursion_limit']
        if state["agent_recursion_validation"] and not state["parse_tool_calling_ok"]:
            return "invalid tool calling"
        return "continue"

    workflow = StateGraph(ChatbotState)
    workflow.add_node("tools_choose_and_results_generation", agent_lambda)
    workflow.add_node("results_evaluation", parse_tool_calling)

    # edge
    workflow.set_entry_point("tools_choose_and_results_generation")
    workflow.add_edge("tools_choose_and_results_generation","results_evaluation")
    workflow.add_conditional_edges(
        "results_evaluation",
        _results_evaluation_route,
        {
            "invalid tool calling": "tools_choose_and_results_generation",
            "continue": END,
            # "no need tool calling": "final_results_preparation",
        }
    )
    app = workflow.compile()
    return app

    
app = None
app_agent = None


def common_entry(event_body):
    """
    Entry point for the Lambda function.
    :param event_body: The event body for lambda function.
    return: answer(str)
    """
    global app,app_agent
    if app is None:
        app = build_graph()
    
    if app_agent is None:
        app_agent = build_agent_graph()

    # debuging
    # TODO only write when run local
    if is_running_local():
        with open("common_entry_workflow.png", "wb") as f:
            f.write(app.get_graph().draw_png())
        
        with open("common_entry_agent_workflow.png", "wb") as f:
            f.write(app_agent.get_graph().draw_png())
            
    ################################################################################
    # prepare inputs and invoke graph
    event_body["chatbot_config"] = parse_common_entry_config(
        event_body["chatbot_config"]
    )
    logger.info(f'event_body:\n{json.dumps(event_body,ensure_ascii=False,indent=2,cls=JSONEncoder)}')
    chatbot_config = event_body["chatbot_config"]
    query = event_body["query"]
    use_history = chatbot_config["use_history"]
    chat_history = event_body["chat_history"] if use_history else []
    stream = event_body["stream"]
    message_id = event_body["custom_message_id"]
    ws_connection_id = event_body["ws_connection_id"]
    enable_trace = chatbot_config["enable_trace"]
    # get all registered tools with parameters
    valid_tool_calling_names = tool_manager.get_names_from_tools_with_parameters()

    # invoke graph and get results
    response = app.invoke(
        {
            "stream": stream,
            "chatbot_config": chatbot_config,
            "query": query,
            "enable_trace": enable_trace,
            "trace_infos": [],
            "message_id": message_id,
            "chat_history": chat_history,
            "agent_chat_history": [],
            "ws_connection_id": ws_connection_id,
            "debug_infos": {},
            "extra_response": {},
            "agent_recursion_limit": chatbot_config['agent_recursion_limit'],
            "current_agent_recursion_num": 0,
            "valid_tool_calling_names": valid_tool_calling_names
        }
    )

    return {"answer": response["answer"], **response["extra_response"]}


main_chain_entry = common_entry
