type ResponseConfig = {
  MaxItems: number;
  PageSize: number;
  StartingToken: string | null;
};

export type LibraryListItem = {
  s3Prefix: string;
  offline: string;
  s3Bucket: string;
  executionId: string;
  executionStatus: string;
  qaEnhance: string;
  operationType: string;
  sfnExecutionId: string;
  indexType: string;
  chatbotId: string;
  createTime: string;
  indexId: string;
  tag: string;
};

export type LibraryListResponse = {
  Items: LibraryListItem[];
  Count: number;
  config: ResponseConfig;
};

export type IntentionsItem = {
  executionId: string;
  executionStatus: string;
  fileName: string;
  index: string;
  model: string;
  validRatio: string;
  chatbotId: string;
  createTime: string;
};

export type IntentionsResponse = {
  items: IntentionsItem[];
  count: number;
  config: ResponseConfig;
};

export type ChatbotsItem = {
  groupName: string;
  chatbotId: string;
  model: {
    model_endpoint: string;
    model_name: string;
  };
  index: IndexItem[];
};

export type ChatbotsResponse = {
  Items: ChatbotsItem[];
  Count: number;
  config: ResponseConfig;
};

export type SessionHistoryItem = {
  sessionId: string;
  userId: string;
  createTimestamp: string;
  latestQuestion: string;
  chatbotId: string;
};

export type SessionHistoryResponse = {
  Items: SessionHistoryItem[];
  Config: ResponseConfig;
  Count: number;
};

export type SessionMessage = {
  messageId: string;
  role: 'ai' | 'human';
  content: string;
  createTimestamp: string;
  chatbotId: string;
  additional_kwargs: {
    figure: AdditionalImageType[];
    ref_docs: DocumentData[];
  };
};

export interface CachedDataType {
  executionId: string;
  fileName: string;
}

export interface IngestResponse {
  execution_id: string;
  input_payload: string;
  step_function_arn: string;
}

export enum BatchOperationStatus {
  RUNNING = 'RUNNING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  TIMED_OUT = 'TIMED_OUT',
  ABORTED = 'ABORTED',
  PENDING_REDRIVE = 'PENDING_REDRIVE',
}

export type LibraryExecutionItem = {
  s3Prefix: string;
  detail?: string;
  s3Bucket: string;
  executionId: string;
  status: string;
  createTime: string;
  s3Path: string;
};

export type IndexItem = {
  name: string;
  type: string;
  description: string;
  tag: string;
};

export type IndexItemTmp = {
  name: string;
  type: string;
  description: string;
  tag: string;
  status: string;
};

export type LibraryExecutionResponse = {
  Items: LibraryExecutionItem[];
  Count: number;
};

export type QAItem = {
  question: string;
  intention: string;
  kwargs: string;
  is_valid: boolean;
};

export type IntentionExecutionItem = {
  s3Prefix: string;
  detail?: string;
  s3Bucket: string;
  executionId: string;
  status: string;
  createTime: string;
  s3Path: string;
  qaList: QAItem[];
};

export type IntentionExecutionResponse = {
  items: IntentionExecutionItem[];
  count: number;
};

export type AdditionalImageType = {
  content_type: string;
  figure_path: string;
};

export interface DocumentData {
  uuid: string;
  page_content: string;
  retrieval_content: string;
  retrieval_score: number;
  rerank_score: number;
  score: number;
  source: string;
  answer: string;
  question: string;
  figure: string[]; // Array of image URLs or other figure-related data
}
export interface MessageDataType {
  message_id: string;
  custom_message_id: string;
  ddb_additional_kwargs: {
    figure: AdditionalImageType[];
  };
  message_type: 'START' | 'CHUNK' | 'END' | 'MONITOR' | 'CONTEXT' | 'REASON'; // START CHUNK END MONITORING
  message: {
    role: string;
    content: string;
  };
  ref_docs: DocumentData[];
}

export interface CreatePromptResponse {
  Message: string;
}

export type PromptItem = {
  uuid: string;
  LastModifiedTime: string;
  // LastModifiedBy: string;
  ModelId: string;
  SortKey: string;
  Scene: string;
  ChatbotId: string;
};

export type PromptResponse = {
  Items: PromptItem[];
  Config: ResponseConfig;
  Count: number;
};

export interface Prompt {
  [key: string]: {
    [subKey: string]: string;
  };
}

export interface GetPromptResponse {
  GroupName: string;
  SortKey: string;
  ModelId: string;
  Scene: string;
  ChatbotId: string;
  Prompt: Prompt;
}

export interface PresignedUrlData {
  url: string;
  s3Bucket: string;
  s3Prefix: string;
}

export interface CreEditChatbotResponse {
  Message: string;
}

export type ChatbotItem = {
  ChatbotId: string;
  LastModifiedTime: string;
  ModelName: string;
  SortKey: string;
  ModelProvider: string;
};

export type ChatbotDetailResponse = {
  chatbotId: string;
  updateTime: string;
  model: {
    model_endpoint: string;
    model_name: string;
    model_provider: string;
    base_url: string;
  };
  index: IndexItem[];
};

export type ChatbotItemDetail = {
  chatbotId: string;
  updateTime: string;
  model: string;
  index: IndexItem[];
  modelProvider: string;
  baseUrl: string;
};

export type ChatbotResponse = {
  Items: ChatbotItem[];
  Config: ResponseConfig;
  Count: number;
};

export type ChatbotIndexResponse = {
  Items: IndexItem[];
  Count: number;
};

export interface Chatbot {
  qd: string;
  qq: string;
  intention: string;
}

export interface chatbotDetail {
  GroupName: string;
  ChatbotId: string;
  Chatbot: Chatbot;
}

export interface PresignedUrlResponse {
  data: PresignedUrlData;
  message: string;
}

export interface indexScanResponse {
  result: string;
}

export interface ExecutionResponse {
  execution_id: string;
  input_payload: string;
  step_function_arn: string;
}
export interface SelectedOption {
  value: string;
  label: string;
}

import { SideNavigationProps } from '@cloudscape-design/components';

// Extend the Link type to include id
export interface CustomLink extends SideNavigationProps.Link {
  id?: string;
  itemID?: string;
  className?: string;
}

// Extend the Section type to include id
export interface CustomSection extends SideNavigationProps.Section {
  id?: string;
  'data-testid'?: string;
}

// Create a union type for all navigation items
export type CustomNavigationItem =
  | CustomLink
  | CustomSection
  | SideNavigationProps.Divider;

export interface ChatSessionType {
  agentId: string;
  clientType: string; // Specific value provided
  connectionId: string;
  createTimestamp: string; // ISO 8601 string format
  lastModifiedTimestamp: string; // ISO 8601 string format
  latestQuestion: string;
  sessionId: string;
  startTime: string; // ISO 8601 string format
  status: string; // Assuming possible status values
  userId: string;
  userName: string;
}

export interface ChatSessionResponse {
  Items: ChatSessionType[];
  Count: number;
}

export interface ChatMessageType {
  messageId: string;
  role: 'agent' | 'user'; // Assuming "agent" and "user" are possible roles
  content: string;
  createTimestamp: string; // ISO 8601 string format
  additional_kwargs: Record<string, unknown>; // Assuming it can be any object
}

export interface ChatMessageResponse {
  Items: ChatMessageType[];
  Count: number;
  Config: ResponseConfig;
}
