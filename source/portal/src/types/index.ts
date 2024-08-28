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
  tag: string;
  chatbotId: string;
  createTime: string;
};

export type IntentionsResponse = {
  Items: IntentionsItem[];
  Count: number;
  config: ResponseConfig;
};

export type SessionHistoryItem = {
  sessionId: string;
  userId: string;
  createTimestamp: string;
  latestQuestion: string;
};

export type SessionHistoryResponse = {
  Items: SessionHistoryItem[];
  Config: ResponseConfig;
  Count: number;
};

export type SessionMessage = {
  role: 'ai' | 'human';
  content: string;
  createTimestamp: string;
  additional_kwargs: {
    figure: AdditionalImageType[];
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

export type LibraryExecutionResponse = {
  Items: LibraryExecutionItem[];
  Count: number;
};

export type QAItem = {
  question: string,
  intention: string,
  kwargs: string
}

export type IntentionExecutionItem = {
  s3Prefix: string;
  detail?: string;
  s3Bucket: string;
  executionId: string;
  status: string;
  createTime: string;
  s3Path: string;
  QAList: QAItem[]
};

export type IntentionExecutionResponse = {
  Items: IntentionExecutionItem[];
  Count: number;
};

export type AdditionalImageType = {
  content_type: string;
  figure_path: string;
};
export interface MessageDataType {
  message_id: string;
  custom_message_id: string;
  ddb_additional_kwargs: {
    figure: AdditionalImageType[];
  };
  message_type: 'START' | 'CHUNK' | 'END' | 'MONITOR' | 'CONTEXT'; // START CHUNK END MONITORING
  message: {
    role: string;
    content: string;
  };
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

export interface CreateChatbotResponse {
  Message: string;
}

export type ChatbotItem = {
  uuid: string;
  LastModifiedTime: string;
  // LastModifiedBy: string;
  ModelId: string;
  SortKey: string;
  Scene: string;
};

export type ChatbotResponse = {
  Items: ChatbotItem[];
  Config: ResponseConfig;
  Count: number;
};

export interface Chatbot {
  [key: string]: {
    [subKey: string]: string;
  };
}

export interface GetChatbotResponse {
  GroupName: string;
  SortKey: string;
  ModelId: string;
  Scene: string;
  Chatbot: Chatbot;
}

export interface PresignedUrlResponse {
  data: PresignedUrlData;
  message: string;
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