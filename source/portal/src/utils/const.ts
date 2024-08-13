import { SelectProps } from '@cloudscape-design/components';
import Library from 'src/pages/library/Library';

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
  'anthropic.claude-3-5-sonnet-20240620-v1:0',
];

export const LLM_BOT_COMMON_MODEL_LIST = [
  'anthropic.claude-3-sonnet-20240229-v1:0',
  'anthropic.claude-3-haiku-20240307-v1:0',
  'anthropic.claude-3-5-sonnet-20240620-v1:0',
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
  {
    label: 'Chat',
    value: 'chat',
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

export const ROUTES = {
  ChatBot: '/',
  Library: '/library',
  LibraryDetail: '/library/detail/:id',
  SessionHistory: '/sessions',
  SessionDetail: '/session/detail/:id',
  PromptList: '/prompts',
  Login: '/login',
  FindPWD: '/find-password',
  Register: '/create-account',
  ChangePWD: '/change-password',
  LoginCallback: '/signin',

  // 其他路径
};

export const TOKEN = "token"
export const USER = "user"
export const API_URL = "api_url"
export const OIDC_REDIRECT_URL = "oidc_uri"
export const PROVIDER = "provider"
export const CLIENT_ID = "client_id"
export const REFRESH_TOKEN = "refresh_token"

export const LOGIN_TYPE = {
  USER: 'user',
  SNS: 'sns',
  OIDC: 'oidc',
};