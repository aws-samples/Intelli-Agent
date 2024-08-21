type ResponseConfig = {
  MaxItems: number;
  PageSize: number;
  StartingToken: string | null;
};

export type LibraryListItem = {
  s3Prefix: string;
  offline: string; // 一直为true？？？
  s3Bucket: string;
  executionId: string;
  executionStatus: string;
  qaEnhance: string; //？？？？
  operationType: string;
  sfnExecutionId: string;
  indexType: string; // qq/qd 
  chatbotId: string; // groupName.lower()
  createTime: string;
  // uiStatus/tag/indexId/embeddingModelType/groupName
};

export type LibraryListResponse = {
  Items: LibraryListItem[];
  Count: number;
  config: ResponseConfig;
};

export type IntentionsItem = {
  s3Prefix: string; // "intentions/Admin/testindeto.xlsx"
  offline: string;  // true
  s3Bucket: string; // intelli-agent-apiconstructllmbotdocumentsfc4f8a7a-6vbr3vihybqs
  executionId: string;
  executionStatus: string;
  operationType: string; // create
  sfnExecutionId: string; // 99041951-b0c5-4b39-9efa-fcee12f751c0
  indexType: string; // 需要吗？intention 需要改job代码
  index: string;
  model: string;
  tag: string;
  chatbotId: string; // 同groupName admin
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
  answer: string,
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
  Prompt: Prompt;
}

export interface PresignedUrlResponse {
  data: string;
  message: string;
  s3Bucket: string;
  s3Prefix: string;
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
