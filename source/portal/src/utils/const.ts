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

export const LAST_VISIT_URL = 'llm-bot-app-last-visit-url';

export const LIBRARY_DEFAULT_PREFIX = 'documents';

export const LLM_BOT_MODEL_LIST = [
  'anthropic.claude-3-sonnet-20240229-v1:0',
  'anthropic.claude-3-haiku-20240307-v1:0',
];

export const LLM_BOT_CHAT_MODE_LIST: SelectProps.Option[] = [
  {
    label: 'Agent',
    value: 'agent',
  },
  {
    label: 'Chat',
    value: 'chat',
  },
  {
    label: 'RAG',
    value: 'rag',
  },
];

export const SCENARIO_LIST: SelectProps.Option[] = [
  {
    label: 'common',
    value: 'common',
  },
  {
    label: 'retail',
    value: 'retail',
  },
];

export const RETAIL_GOODS_LIST: SelectProps.Option[] = [
  {
    label: '男款长袖T-shirt-751501610432',
    value: '751501610432',
  },
  {
    label: '女子运动鞋-756327274174',
    value: '756327274174',
  },
];
