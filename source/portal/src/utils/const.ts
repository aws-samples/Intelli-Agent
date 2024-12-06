import { SelectProps } from '@cloudscape-design/components';

export const DEFAULT_ZH_LANG = 'zh';
export const DEFAULT_EN_LANG = 'en';
export const ZH_LANGUAGE_LIST = [DEFAULT_ZH_LANG, 'zh-CN', 'zh-cn', 'zh_CN'];

export const ZH_TEXT = '简体中文';
export const EN_TEXT = 'English(US)';
export const LANGUAGE_ITEMS = [
  { id: DEFAULT_EN_LANG, text: EN_TEXT },
  { id: DEFAULT_ZH_LANG, text: ZH_TEXT },
];

export const INDEX_TYPE_OPTIONS = [
  {label: "qq", value: "qq"},
  {label: "qd", value: "qd"},
  {label: "intention", value: "intention"}
]

export const LAST_VISIT_URL = 'llm-bot-app-last-visit-url';

export const LIBRARY_DEFAULT_PREFIX = 'documents';

export const LLM_BOT_MODEL_LIST = [
  'anthropic.claude-3-sonnet-20240229-v1:0',
  'anthropic.claude-3-haiku-20240307-v1:0',
];

export const LLM_BOT_COMMON_MODEL_LIST = [
  'anthropic.claude-3-sonnet-20240229-v1:0',
  'anthropic.claude-3-haiku-20240307-v1:0',
  'anthropic.claude-3-5-sonnet-20241022-v2:0',
  'anthropic.claude-3-5-haiku-20241022-v1:0',
  'meta.llama3-1-70b-instruct-v1:0',
  'mistral.mistral-large-2407-v1:0',
  'cohere.command-r-plus-v1:0',
  'us.amazon.nova-pro-v1:0',
];

export const LLM_BOT_RETAIL_MODEL_LIST = [
  'qwen2-72B-instruct',
  'anthropic.claude-3-5-sonnet-20240620-v1:0',
];

export const LLM_BOT_CHAT_MODE_LIST: SelectProps.Option[] = [
  {
    label: 'Agent',
    value: 'agent',
  },
];

export const LLM_BOT_CHATBOT_LIST: SelectProps.Option[] = [
  {
    label: 'admin',
    value: 'admin',
  },
];

export const SCENARIO_LIST: SelectProps.Option[] = [
  {
    label: 'common',
    value: 'common',
  },
];

export const RETAIL_GOODS_LIST: SelectProps.Option[] = [
  {
    label: '女子运动鞋-756327274174',
    value: '756327274174',
  },
  {
    label: '男款外套上衣-743891340644',
    value: '743891340644',
  },
];

export const DOC_INDEX_TYPE_LIST: SelectProps.Option[] = [
  {
    label: 'qd',
    value: 'qd',
  },
  {
    label: 'qq',
    value: 'qq',
  },
];

export const DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

export const EMBEDDING_MODEL_LIST = [
  {"model_id": "amazon.titan-embed-text-v2:0", "model_name": "amazon.titan-embed-text-v2:0"},
  {"model_id": "cohere.embed-english-v3", "model_name": "cohere.embed-english-v3"},
  {"model_id": "amazon.titan-embed-text-v1", "model_name": "amazon.titan-embed-text-v1"}
]

export const RESOURCE_QQ_TEMPLATE = "https://ai-customer-service-resources.s3.us-west-2.amazonaws.com/qq_match_template.xlsx"
