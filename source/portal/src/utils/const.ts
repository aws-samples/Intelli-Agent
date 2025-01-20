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
  { label: 'qq', value: 'qq' },
  { label: 'qd', value: 'qd' },
  { label: 'intention', value: 'intention' },
];

export const LAST_VISIT_URL = 'llm-bot-app-last-visit-url';

export const LIBRARY_DEFAULT_PREFIX = 'documents';

export const LLM_BOT_MODEL_LIST = [
  'anthropic.claude-3-sonnet-20240229-v1:0',
  'anthropic.claude-3-haiku-20240307-v1:0',
];

export const LLM_BOT_COMMON_MODEL_LIST = [
  {
    label: 'Amazon Nova',
    options: [
      { label: 'us.amazon.nova-pro-v1:0', value: 'us.amazon.nova-pro-v1:0' },
      { label: 'us.amazon.nova-lite-v1:0', value: 'us.amazon.nova-lite-v1:0' },
      {
        label: 'us.amazon.nova-micro-v1:0',
        value: 'us.amazon.nova-micro-v1:0',
      },
    ],
  },
  {
    label: 'Claude',
    options: [
      {
        label: 'anthropic.claude-3-sonnet-20240229-v1:0',
        value: 'anthropic.claude-3-sonnet-20240229-v1:0',
      },
      {
        label: 'us.anthropic.claude-3-opus-20240229-v1:0',
        value: 'us.anthropic.claude-3-opus-20240229-v1:0',
      },
      {
        label: 'anthropic.claude-3-haiku-20240307-v1:0',
        value: 'anthropic.claude-3-haiku-20240307-v1:0',
      },
      {
        label: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
        value: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
      },
      {
        label: 'anthropic.claude-3-5-haiku-20241022-v1:0',
        value: 'anthropic.claude-3-5-haiku-20241022-v1:0',
      },
      {
        label: 'us.anthropic.claude-3-sonnet-20240229-v1:0',
        value: 'us.anthropic.claude-3-sonnet-20240229-v1:0',
      },
      {
        label: 'us.anthropic.claude-3-opus-20240229-v1:0',
        value: 'us.anthropic.claude-3-opus-20240229-v1:0',
      },
      {
        label: 'us.anthropic.claude-3-haiku-20240307-v1:0',
        value: 'us.anthropic.claude-3-haiku-20240307-v1:0',
      },
      {
        label: 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
        value: 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
      },
      {
        label: 'us.anthropic.claude-3-5-haiku-20241022-v1:0',
        value: 'us.anthropic.claude-3-5-haiku-20241022-v1:0',
      },
      {
        label: 'eu.anthropic.claude-3-sonnet-20240229-v1:0',
        value: 'eu.anthropic.claude-3-sonnet-20240229-v1:0',
      },
      {
        label: 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0',
        value: 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0',
      },
      {
        label: 'eu.anthropic.claude-3-haiku-20240307-v1:0',
        value: 'eu.anthropic.claude-3-haiku-20240307-v1:0',
      },
      {
        label: 'apac.anthropic.claude-3-sonnet-20240229-v1:0',
        value: 'apac.anthropic.claude-3-sonnet-20240229-v1:0',
      },
      {
        label: 'apac.anthropic.claude-3-5-sonnet-20240620-v1:0',
        value: 'apac.anthropic.claude-3-5-sonnet-20240620-v1:0',
      },
      {
        label: 'apac.anthropic.claude-3-haiku-20240307-v1:0',
        value: 'apac.anthropic.claude-3-haiku-20240307-v1:0',
      },
    ],
  },
  {
    label: 'Llama',
    options: [
      {
        lable: 'meta.llama3-1-70b-instruct-v1:0',
        value: 'meta.llama3-1-70b-instruct-v1:0',
      },
      {
        label: 'us.meta.llama3-1-70b-instruct-v1:0',
        value: 'us.meta.llama3-1-70b-instruct-v1:0',
      },
    ],
  },
  {
    label: 'Mistral',
    options: [
      {
        label: 'mistral.mistral-large-2407-v1:0',
        value: 'mistral.mistral-large-2407-v1:0',
      },
    ],
  },
  {
    label: 'Cohere',
    options: [
      {
        label: 'cohere.command-r-plus-v1:0',
        value: 'cohere.command-r-plus-v1:0',
      },
    ],
  },
];

export const LLM_BOT_RETAIL_MODEL_LIST = [
  {
    label: 'Qwen',
    options: [
      {
        label: 'qwen2-72B-instruct',
        value: 'qwen2-72B-instruct',
      },
    ],
  },
  {
    label: 'Claude',
    options: [
      {
        label: 'anthropic.claude-3-5-sonnet-20240620-v1:0',
        value: 'anthropic.claude-3-5-sonnet-20240620-v1:0',
      },
    ],
  },
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

export const MODEL_TYPE_LIST: SelectProps.Option[] = [
  {
    label: 'Bedrock',
    value: 'Bedrock',
  },
  {
    label: 'Bedrock API',
    value: 'Bedrock API',
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

export const DEFAULT_EMBEDDING_MODEL = 'amazon.titan-embed-text-v2:0';

export const EMBEDDING_MODEL_LIST = [
  {
    model_id: 'amazon.titan-embed-text-v2:0',
    model_name: 'amazon.titan-embed-text-v2:0',
  },
  {
    model_id: 'cohere.embed-english-v3',
    model_name: 'cohere.embed-english-v3',
  },
  {
    model_id: 'amazon.titan-embed-text-v1',
    model_name: 'amazon.titan-embed-text-v1',
  },
];

export const RESOURCE_QQ_TEMPLATE =
  'https://ai-customer-service-resources.s3.us-west-2.amazonaws.com/qq_match_template.xlsx';

export const CURRENT_CHAT_BOT = 'current_chat_bot';
export const USE_CHAT_HISTORY = 'use_chat_history';
export const ENABLE_TRACE = 'enable_trace';
export const ONLY_RAG_TOOL = 'only_rag_tool';
export const MODEL_TYPE = 'modelType';
export const MODEL_OPTION = 'model';
export const MAX_TOKEN = 'max_token';
export const TEMPERATURE = 'temperature';
export const ROUND = 'round';
export const TOPK = 'topK';
export const SCORE = 'score';
export const ADITIONAL_SETTINGS = 'additional_settings';
export const HISTORY_CHATBOT_ID = 'history_chatbot_id';
