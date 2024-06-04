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
  'anthropic.claude-3-haiku-20240307-v1:0',
  'anthropic.claude-3-sonnet-20240229-v1:0',
];

export const LLM_BOT_CHAT_MODE_LIST: SelectProps.Option[] = [
  {
    label: 'Chat',
    value: 'chat',
  },
  {
    label: 'RAG',
    value: 'rag',
  },
  {
    label: 'Agent',
    value: 'agent',
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
    label: '760740990909',
    value: '760740990909',
  },
  {
    label: '714702761908',
    value: '714702761908',
  },
  {
    label: '743353945710',
    value: '743353945710',
  },
  {
    label: '675124761798',
    value: '675124761798',
  },
  {
    label: '728966930906',
    value: '728966930906',
  },
  {
    label: '745329022773',
    value: '745329022773',
  },
  {
    label: '712058889741',
    value: '712058889741',
  },
  {
    label: '725289865739',
    value: '725289865739',
  },
  {
    label: '687746328768',
    value: '687746328768',
  },
  {
    label: '757661371942',
    value: '757661371942',
  },
  {
    label: '636833619119',
    value: '636833619119',
  },
  {
    label: '759408173451',
    value: '759408173451',
  },
  {
    label: '763727004470',
    value: '763727004470',
  },
  {
    label: '751465119152',
    value: '751465119152',
  },
  {
    label: '766158164989',
    value: '766158164989',
  },
  {
    label: '654826013986',
    value: '654826013986',
  },
  {
    label: '748090908717',
    value: '748090908717',
  },
  {
    label: '751501610432',
    value: '751501610432',
  },
  {
    label: '760601512644',
    value: '760601512644',
  },
  {
    label: '689718325885',
    value: '689718325885',
  },
  {
    label: '708213616110',
    value: '708213616110',
  },
  {
    label: '745288790794',
    value: '745288790794',
  },
  {
    label: '736428008249',
    value: '736428008249',
  },
  {
    label: '736618025233',
    value: '736618025233',
  },
  {
    label: '736844915358',
    value: '736844915358',
  },
  {
    label: '742727909028',
    value: '742727909028',
  },
  {
    label: '738704284084',
    value: '738704284084',
  },
  {
    label: '742563760024',
    value: '742563760024',
  },
];
