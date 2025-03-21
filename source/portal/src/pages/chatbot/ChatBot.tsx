import React, { useContext, useEffect, useState, useRef } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import Message from './components/Message';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import {
  Autosuggest,
  Box,
  Button,
  Container,
  ContentLayout,
  ExpandableSection,
  FormField,
  Grid,
  Header,
  Input,
  Select,
  SelectProps,
  SpaceBetween,
  Spinner,
  StatusIndicator,
  Textarea,
  Toggle
} from '@cloudscape-design/components';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { identity } from 'lodash';
import ConfigContext from 'src/context/config-context';
import { useAuth } from 'react-oidc-context';
import {
  LLM_BOT_COMMON_MODEL_LIST,
  MODEL_TYPE_LIST,
  MODEL_TYPE,
  MAX_TOKEN,
  TEMPERATURE,
  ADITIONAL_SETTINGS,
  USE_CHAT_HISTORY,
  ENABLE_TRACE,
  ONLY_RAG_TOOL,
  MODEL_OPTION,
  CURRENT_CHAT_BOT,
  TOPK_KEYWORD,
  TOPK_EMBEDDING,
  TOPK_RERANK,
  KEYWORD_SCORE,
  EMBEDDING_SCORE,
  ROUND,
  HISTORY_CHATBOT_ID,
  BR_API_MODEL_LIST,
  OPENAI_API_MODEL_LIST,
  SHOW_FIGURES,
  API_ENDPOINT,
  API_KEY_ARN,
  ROUTES,
  SILICON_FLOW_API_MODEL_LIST,
  OIDC_STORAGE,
  SAGEMAKER_MODEL_LIST
} from 'src/utils/const';
import { v4 as uuidv4 } from 'uuid';
import { MessageDataType, SessionMessage } from 'src/types';
import { getCredentials, isValidJson } from 'src/utils/utils';

interface MessageType {
  messageId: string;
  type: 'ai' | 'human';
  message: {
    data: string;
    monitoring: string;
  };
  attachments?: File[];
}

interface ChatBotProps {
  historySessionId?: string;
}

const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return url.startsWith('http://') || url.startsWith('https://');
  } catch {
    return false;
  }
};

const isValidArn = (arn: string): boolean => {
  // AWS Global and China ARN patterns
  // arn:aws:secretsmanager:region:account-id:secret:name
  // arn:aws-cn:secretsmanager:region:account-id:secret:name
  const arnPattern =
    /^arn:aws(?:-cn)?:secretsmanager:[a-z0-9-]+:\d{12}:secret:.+$/;
  return arnPattern.test(arn);
};

const ChatBot: React.FC<ChatBotProps> = (props: ChatBotProps) => {
  const { historySessionId } = props;
  const [loadingChatBots, setLoadingChatBots] = useState(false);
  // const [loadingModel, setLoadingModel] = useState(false);
  // const [loadingModelList, setLoadingModelList] = useState(false);
  // const localScenario = localStorage.getItem(MODEL_TYPE);
  const localMaxToken = localStorage.getItem(MAX_TOKEN);
  const localTemperature = localStorage.getItem(TEMPERATURE);
  const localConfig = localStorage.getItem(ADITIONAL_SETTINGS);
  const localRound = localStorage.getItem(ROUND);
  const localTopKKeyword = localStorage.getItem(TOPK_KEYWORD);
  const localTopKEmbedding = localStorage.getItem(TOPK_EMBEDDING);
  const localTopKRerank = localStorage.getItem(TOPK_RERANK);
  const localKeywordScore = localStorage.getItem(KEYWORD_SCORE);
  const localEmbeddingScore = localStorage.getItem(EMBEDDING_SCORE);
  const localApiEndpoint = localStorage.getItem(API_ENDPOINT);
  const localApiKeyArn = localStorage.getItem(API_KEY_ARN);
  const config = useContext(ConfigContext);
  const { t } = useTranslation();
  const auth = useAuth();
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [messages, setMessages] = useState<MessageType[]>([
    {
      messageId: uuidv4(),
      type: 'ai',
      message: {
        data: t('welcomeMessage'),
        monitoring: '',
      },
    },
  ]);
  const [userMessage, setUserMessage] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const oidc = JSON.parse(localStorage.getItem(OIDC_STORAGE) || '');
  let wsUrl = `${config?.websocket}?idToken=${getCredentials().idToken}&provider=${oidc.provider}&clientId=${config?.oidcClientId}&poolId=${config?.oidcPoolId}`;
  if (oidc.provider === 'authing') {
    wsUrl = `${config?.websocket}?idToken=${getCredentials().access_token}&provider=${oidc.provider}&clientId=${oidc.clientId}&redirectUri=${oidc.redirectUri}`;
  }
  const { lastMessage, sendMessage, readyState } = useWebSocket(wsUrl, {
    onOpen: () => console.log('opened'),
    shouldReconnect: () => true,
  });
  const [currentAIMessage, setCurrentAIMessage] = useState('');
  const [currentMonitorMessage, setCurrentMonitorMessage] = useState('');
  const [currentAIMessageId, setCurrentAIMessageId] = useState('');
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [modelOption, setModelOption] = useState('');
  const [modelList, setModelList] = useState<SelectProps.Option[]>([]);
  const [chatbotList, setChatbotList] = useState<SelectProps.Option[]>([]);
  const [apiEndpointOption, setApiEndpointOption] = useState<SelectProps.Option>(null as any)
  const [chatbotOption, setChatbotOption] = useState<SelectProps.Option>(
    {label: 'admin', value: 'admin'} as any,
  );
  const [useChatHistory, setUseChatHistory] = useState(
    localStorage.getItem(USE_CHAT_HISTORY) == null ||
      localStorage.getItem(USE_CHAT_HISTORY) == 'true'
      ? true
      : false,
  );
  const [enableTrace, setEnableTrace] = useState(
    localStorage.getItem(ENABLE_TRACE) == null ||
      localStorage.getItem(ENABLE_TRACE) == 'true'
      ? true
      : false,
  );
  const [showTrace, setShowTrace] = useState(enableTrace);
  const [onlyRAGTool, setOnlyRAGTool] = useState(
    localStorage.getItem(ONLY_RAG_TOOL) == null ||
      localStorage.getItem(ONLY_RAG_TOOL) == 'true'
      ? true
      : false,
  );
  const [isComposing, setIsComposing] = useState(false);
  const [modelType, setModelType] = useState<SelectProps.Option>(
    MODEL_TYPE_LIST[0],
  );
  const defaultConfig = {
    temperature: '0.01',
    maxToken: '1000',
    maxRounds: '7',
    topKKeyword: '5',
    topKEmbedding: '5',
    topKRerank: '10',
    keywordScore: '0.4',
    embeddingScore: '0.4',
    additionalConfig: '',
  };

  const [sessionId, setSessionId] = useState(historySessionId);

  const [temperature, setTemperature] = useState<string>(
    localTemperature ?? defaultConfig.temperature,
  );
  const [maxToken, setMaxToken] = useState<string>(
    localMaxToken ?? defaultConfig.maxToken,
  );
  const [maxRounds, setMaxRounds] = useState<string>(
    localRound ?? defaultConfig.maxRounds,
  );
  const [topKKeyword, setTopKKeyword] = useState<string>(
    localTopKKeyword ?? defaultConfig.topKKeyword,
  );
  const [topKEmbedding, setTopKEmbedding] = useState<string>(
    localTopKEmbedding ?? defaultConfig.topKEmbedding,
  );
  const [topKRerank, setTopKRerank] = useState<string>(
    localTopKRerank ?? defaultConfig.topKRerank,
  );
  const [keywordScore, setKeywordScore] = useState<string>(
    localKeywordScore ?? defaultConfig.keywordScore,
  );
  const [embeddingScore, setEmbeddingScore] = useState<string>(
    localEmbeddingScore ?? defaultConfig.embeddingScore,
  );
  const [additionalConfig, setAdditionalConfig] = useState(
    localConfig ?? defaultConfig.additionalConfig,
  );
  const [topKKeywordError, setTopKKeywordError] = useState('');
  const [topKEmbeddingError, setTopKEmbeddingError] = useState('');
  const [topKRerankError, setTopKRerankError] = useState('');
  const [maxRoundsError, setMaxRoundsError] = useState('');
  const [keywordScoreError, setKeywordScoreError] = useState('');
  const [embeddingScoreError, setEmbeddingScoreError] = useState('');

  const [endPoint, setEndPoint] = useState('');
  const [showEndpoint, setShowEndpoint] = useState(false);
  const [endPointError, setEndPointError] = useState('');
  const [showMessageError, setShowMessageError] = useState(false);
  const [isMessageEnd, setIsMessageEnd] = useState(false);
  const [modelError, setModelError] = useState('');
  const [temperatureError, setTemperatureError] = useState('');
  const [maxTokenError, setMaxTokenError] = useState('');
  const [modelSettingExpand, setModelSettingExpand] = useState(false);
  const [additionalConfigError, setAdditionalConfigError] = useState('');
  const [apiEndpointError, setApiEndpointError] = useState('');
  const [apiKeyArnError, setApiKeyArnError] = useState('');
  const [apiEndpoint, setApiEndpoint] = useState(localApiEndpoint ?? '');
  const [apiKeyArn, setApiKeyArn] = useState(localApiKeyArn ?? '');
  const [endpoints, setEndpoints] = useState<{label: string, value: string}[]>([])

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'loading',
    [ReadyState.OPEN]: 'success',
    [ReadyState.CLOSING]: 'closing',
    [ReadyState.CLOSED]: 'error',
    [ReadyState.UNINSTANTIATED]: 'pending',
  }[readyState];

  // Define an async function to get the data
  const fetchData = useAxiosRequest();

  // const [chatbotModelProvider, setChatbotModelProvider] = useState<{
  //   [key: string]: string;
  // }>({});

  // const [modelProviderHint, setModelProviderHint] = useState('');

  const startNewChat = () => {
    [
      CURRENT_CHAT_BOT,
      ENABLE_TRACE,
      MAX_TOKEN,
      MODEL_OPTION,
      ONLY_RAG_TOOL,
      MODEL_TYPE,
      TEMPERATURE,
      USE_CHAT_HISTORY,
    ].forEach((item) => {
      localStorage.removeItem(item);
    });
    // localStorage.()
    setChatbotOption(chatbotList[0]);
    setModelType(MODEL_TYPE_LIST[0]);
    setMaxToken(defaultConfig.maxToken);
    setMaxRounds(defaultConfig.maxRounds);
    setTemperature(defaultConfig.temperature);
    // setTopKRetrievals(defaultConfig.topKRetrievals);
    setTopKKeyword(defaultConfig.topKKeyword);
    setTopKEmbedding(defaultConfig.topKEmbedding);
    setTopKRerank(defaultConfig.topKRerank);
    setKeywordScore(defaultConfig.keywordScore);
    setEmbeddingScore(defaultConfig.embeddingScore);
    setUserMessage('');
    setAdditionalConfig('');
    // setModelOption(optionList?.[0]?.value ?? '')
    setSessionId(uuidv4());
    getWorkspaceList();
    setMessages([
      {
        messageId: uuidv4(),
        type: 'ai',
        message: {
          data: t('welcomeMessage'),
          monitoring: '',
        },
      },
    ]);
  };

  const getWorkspaceList = async () => {
    try {
      const data = await fetchData({
        url: 'chatbot-management/chatbots',
        method: 'get',
      });
      const chatbots: { chatbotId: string; ModelProvider: string }[] =
        data.items;
      const getChatbots = chatbots.map((item) => {
        // setChatbotModelProvider((prev) => ({
        //   ...prev,
        //   [item.chatbotId]: item.ModelProvider,
        // }));
        return {
          label: item.chatbotId,
          value: item.chatbotId,
        };
      });
      setChatbotList(getChatbots);

      // First try to get chatbotId from history if it exists
      const historyChatbotId = localStorage.getItem(HISTORY_CHATBOT_ID);
      const localChatBot = localStorage.getItem(CURRENT_CHAT_BOT);

      if (
        historyChatbotId &&
        getChatbots.some((bot) => bot.value === historyChatbotId)
      ) {
        // If history chatbotId exists and is valid, use it
        setChatbotOption({
          label: historyChatbotId,
          value: historyChatbotId,
        });
      } else if (localChatBot !== null) {
        // Otherwise fall back to local storage
        setChatbotOption(JSON.parse(localChatBot));
      } else {
        // Finally fall back to first chatbot
        setChatbotOption(getChatbots[0]);
      }
    } catch (error) {
      console.error(error);
      return [];
    }
  };

  const getSessionHistoryById = async () => {
    try {
      setLoadingHistory(true);
      const data = await fetchData({
        url: `sessions/${historySessionId}/messages`,
        method: 'get',
        params: {
          page_size: 9999,
          max_items: 9999,
        },
      });
      const sessionMessage: SessionMessage[] = data.Items;

      // Get chatbotId from first message if available
      if (sessionMessage && sessionMessage.length > 0) {
        const chatbotId = sessionMessage[0].chatbotId;
        // Store chatbotId for use in getWorkspaceList
        localStorage.setItem(HISTORY_CHATBOT_ID, chatbotId);
      }

      setMessages(
        sessionMessage.map((msg) => {
          let messageContent = msg.content;
          // Handle AI images message
          if (
            showFigures &&
            msg.role === 'ai' &&
            msg.additional_kwargs?.figure?.length > 0
          ) {
            msg.additional_kwargs.figure.forEach((item) => {
              messageContent += ` \n ![${item.content_type}](/${encodeURIComponent(item.figure_path)})`;
            });
          }
          return {
            messageId: msg.messageId,
            type: msg.role,
            message: {
              data: messageContent,
              monitoring: '',
            },
          };
        }),
      );
      setLoadingHistory(false);
    } catch (error) {
      console.error(error);
      return [];
    }
  };
  useEffect(() => {
    const initializeChatbot = async () => {
      setLoadingChatBots(true)
      if (historySessionId) {
        // Wait for getSessionHistoryById to complete to set history chatbotId
        await getSessionHistoryById();
      } else {
        setSessionId(uuidv4());
      }
      // Call getWorkspaceList after getSessionHistoryById
      getWorkspaceList();
    };

    const fetchEndpoints = async () =>{
      const tempModels: { label: string; value: string }[] = [];
      const data = await fetchData({
        url: 'model-management/endpoints',
        method: 'get'
      });
      data.endpoints.forEach((endpoint: any) => {
        tempModels.push({
          label: endpoint.endpoint_name,
          value: endpoint.endpoint_name,
        });
      });
      setEndpoints(tempModels)
      setApiEndpointOption(tempModels[0])
    }
    fetchEndpoints();

    initializeChatbot();
    setLoadingChatBots(false)
  }, []);

  useEffect(() => {
    if (chatbotOption) {
      localStorage.setItem(CURRENT_CHAT_BOT, JSON.stringify(chatbotOption));
    }
  }, [chatbotOption]);

  useEffect(() => {
    localStorage.setItem(USE_CHAT_HISTORY, useChatHistory ? 'true' : 'false');
  }, [useChatHistory]);

  useEffect(() => {
    localStorage.setItem(ENABLE_TRACE, enableTrace ? 'true' : 'false');
    if (enableTrace) {
      setShowTrace(true);
    } else {
      setShowTrace(false);
    }
  }, [enableTrace]);

  useEffect(() => {
    if (modelType) {
      localStorage.setItem(MODEL_TYPE, JSON.stringify(modelType));
    }
  }, [modelType]);

  useEffect(() => {
    if (maxRounds) {
      localStorage.setItem(ROUND, maxRounds);
    }
  }, [maxRounds]);

  useEffect(() => {
    if (topKKeyword) {
      localStorage.setItem(TOPK_KEYWORD, topKKeyword);
    }
  }, [topKKeyword]);

  useEffect(() => {
    if (topKEmbedding) {
      localStorage.setItem(TOPK_EMBEDDING, topKEmbedding);
    }
  }, [topKEmbedding]);

  useEffect(() => {
    if (topKRerank) {
      localStorage.setItem(TOPK_RERANK, topKRerank);
    }
  }, [topKRerank]);

  useEffect(() => {
    if (keywordScore) {
      localStorage.setItem(KEYWORD_SCORE, keywordScore);
    }
  }, [keywordScore]);

  useEffect(() => {
    if (embeddingScore) {
      localStorage.setItem(EMBEDDING_SCORE, embeddingScore);
    }
  }, [embeddingScore]);

  useEffect(() => {
    localStorage.setItem(ONLY_RAG_TOOL, onlyRAGTool ? 'true' : 'false');
  }, [onlyRAGTool]);

  useEffect(() => {
    if (modelOption) {
      localStorage.setItem(MODEL_OPTION, modelOption);
    }
  }, [modelOption]);

  useEffect(() => {
    if (maxToken) {
      localStorage.setItem(MAX_TOKEN, maxToken);
    }
  }, [maxToken]);

  useEffect(() => {
    if (temperature) {
      localStorage.setItem(TEMPERATURE, temperature);
    }
  }, [temperature]);

  useEffect(() => {
    if (additionalConfig) {
      localStorage.setItem(ADITIONAL_SETTINGS, additionalConfig);
    }
  }, [additionalConfig]);

  useEffect(() => {
    if (apiEndpoint) {
      localStorage.setItem(API_ENDPOINT, apiEndpoint);
    }
  }, [apiEndpoint]);

  useEffect(() => {
    if (apiKeyArn) {
      localStorage.setItem(API_KEY_ARN, apiKeyArn);
    }
  }, [apiKeyArn]);

  const handleAIMessage = (message: MessageDataType) => {
    // console.info('handleAIMessage:', message);
    if (message.message_type === 'START') {
      console.info('message started');
    } else if (message.message_type === 'CHUNK') {
      setCurrentAIMessage((prev) => {
        return prev + (message?.message?.content ?? '');
      });
    } else if (message.message_type === 'CONTEXT') {
      // handle context message
      if (showFigures && message.ddb_additional_kwargs?.figure?.length > 0) {
        message.ddb_additional_kwargs.figure.forEach((item) => {
          if (item.content_type === 'md_image') {
            setCurrentAIMessage((prev) => {
              return prev + ` \n ![${item.content_type}](${item.figure_path})`;
            });
          } else {
            setCurrentAIMessage((prev) => {
              return (
                prev +
                ` \n ![${item.content_type}](/${encodeURIComponent(item.figure_path)})`
              );
            });
          }
        });
      }
    } else if (message.message_type === 'END') {
      console.info('message ended');
      setCurrentAIMessageId(message.message_id);
      setAiSpeaking(false);
      setIsMessageEnd(true);
    }
  };

  const inputElement = document.querySelector('input');

  if (inputElement) {
    inputElement.addEventListener('compositionstart', () => {
      setIsComposing(true);
    });
    inputElement.addEventListener('compositionend', () => {
      setIsComposing(false);
    });
  }

  useEffect(() => {
    if (lastMessage !== null) {
      const message: MessageDataType = JSON.parse(lastMessage.data);
      if (message.message_type === 'MONITOR') {
        setCurrentMonitorMessage((prev) => {
          return prev + (message?.message ?? '');
        });
      } else {
        handleAIMessage(message);
      }
    }
  }, [lastMessage]);

  useEffect(() => {
    if (isMessageEnd) {
      setAiSpeaking(false);
      setMessages((prev) => {
        return [
          ...prev,
          {
            messageId: currentAIMessageId,
            type: 'ai',
            message: {
              data: currentAIMessage,
              monitoring: currentMonitorMessage,
            },
          },
        ];
      });
    }
  }, [isMessageEnd]);

  const handleClickSendMessage = (customQuery?: string) => {
    if (aiSpeaking) {
      return;
    }

    const messageToSend = customQuery ?? userMessage;

    if (!messageToSend.trim() && selectedFiles.length === 0) {
      setShowMessageError(true);
      return;
    }
    // validate websocket status
    if (readyState !== ReadyState.OPEN) {
      return;
    }
    // validate model settings
    if (
      modelType.value === 'Bedrock API' ||
      modelType.value === 'OpenAI API' ||
      modelType.value === 'siliconflow'
    ) {
      if (!apiEndpoint.trim()) {
        setApiEndpointError(t('validation.requireApiEndpoint'));
        setModelSettingExpand(true);
        return;
      }
      if (!apiKeyArn.trim()) {
        setApiKeyArnError(t('validation.requireApiKeyArn'));
        setModelSettingExpand(true);
        return;
      }
    } else {
      if(modelType.value === 'SageMaker' && !apiEndpoint.trim()){
        setApiEndpointError(t('validation.requireSagemakerEndpoint'));
        setModelSettingExpand(true);
        return;
      }

      if (!modelOption.trim()) {
        setModelError(t('validation.requireModel'));
        setModelSettingExpand(true);
        return;
      }
    }
    if (!temperature.trim()) {
      setTemperatureError(t('validation.requireTemperature'));
      setModelSettingExpand(true);
      return;
    }
    if (!maxToken.trim()) {
      setMaxTokenError(t('validation.requireMaxTokens'));
      setModelSettingExpand(true);
      return;
    }
    if (parseInt(maxToken) < 1) {
      setMaxTokenError(t('validation.maxTokensRange'));
      setModelSettingExpand(true);
      return;
    }

    if (!maxRounds.trim()) {
      setMaxRoundsError(t('validation.requireMaxRounds'));
      setModelSettingExpand(true);
      return;
    }

    if (parseInt(maxRounds) < 0) {
      setMaxRoundsError(t('validation.maxRoundsRange'));
      setModelSettingExpand(true);
      return;
    }

    if (!topKRerank.trim()) {
      setTopKRerankError(t('validation.requireTopKRerank'));
      setModelSettingExpand(true);
      return;
    }

    if (!topKKeyword.trim()) {
      setTopKKeywordError(t('validation.requireTopKKeyword'));
      setModelSettingExpand(true);
      return;
    }

    if (!topKEmbedding.trim()) {
      setTopKEmbeddingError(t('validation.requireTopKEmbedding'));
      setModelSettingExpand(true);
      return;
    }
    if (!topKRerank.trim()) {
      setTopKRerankError(t('validation.requireTopKRerank'));
      setModelSettingExpand(true);
      return;
    }

    // if (parseInt(topKRetrievals) < 1) {
    //   setTopKRetrievalsError(t('validation.topKRetrievals'));
    //   setModelSettingExpand(true);
    //   return;
    // }

    if (parseFloat(temperature) < 0.0 || parseFloat(temperature) > 1.0) {
      setTemperatureError(t('validation.temperatureRange'));
      setModelSettingExpand(true);
      return;
    }

    if (!keywordScore.trim()) {
      setKeywordScoreError(t('validation.requireKeywordScore'));
      setModelSettingExpand(true);
      return;
    }

    if (!embeddingScore.trim()) {
      setEmbeddingScoreError(t('validation.requireEmbeddingScore'));
      setModelSettingExpand(true);
      return;
    }

    // validate endpoint
    if (modelType.value === 'Bedrock API' && !endPoint.trim()) {
      setEndPointError(t('validation.requireEndPoint'));
      setModelSettingExpand(true);
      return;
    }

    // validate additional config
    if (additionalConfig.trim() && !isValidJson(additionalConfig)) {
      setAdditionalConfigError(t('validation.invalidJson'));
      setModelSettingExpand(true);
      return;
    }

    setUserMessage('');
    setAiSpeaking(true);
    setCurrentAIMessage('');
    setCurrentMonitorMessage('');
    setIsMessageEnd(false);

    const groupName: string[] = auth?.user?.profile?.['cognito:groups'] as any;
    let message = {
      query: messageToSend,
      entry_type: 'common',
      session_id: sessionId,
      user_id: auth?.user?.profile?.['cognito:username'] || 'default_user_id',
      chatbot_config: {
        max_rounds_in_memory: parseInt(maxRounds),
        group_name: groupName?.[0] ?? 'Admin',
        chatbot_id: chatbotOption.value ?? 'admin',
        chatbot_mode: 'agent',
        use_history: useChatHistory,
        enable_trace: enableTrace,
        use_websearch: true,
        google_api_key: '',
        default_llm_config: {
          model_id: modelOption,
          endpoint_name:
            modelOption === 'qwen2-72B-instruct' ? endPoint.trim() : apiEndpoint,
          provider: modelType.value,
          base_url:
            modelType.value === 'Bedrock API' ||
              modelType.value === 'OpenAI API' ||
              modelType.value === 'siliconflow'
              ? apiEndpoint.trim()
              : '',
          api_key_arn:
            modelType.value === 'Bedrock API' ||
              modelType.value === 'OpenAI API' ||
              modelType.value === 'siliconflow'
              ? apiKeyArn.trim()
              : '',
          model_kwargs: {
            temperature: parseFloat(temperature),
            max_tokens: parseInt(maxToken),
          },
        },
        default_retriever_config: {
          private_knowledge: {
            bm25_search_top_k: parseInt(topKKeyword),
            bm25_search_score: parseFloat(keywordScore),
            vector_search_top_k: parseInt(topKEmbedding),
            vector_search_score: parseFloat(embeddingScore),
            rerank_top_k: parseInt(topKRerank)
          }
        },
        agent_config: {
          only_use_rag_tool: onlyRAGTool,
        },
      },
    };

    // add additional config
    if (additionalConfig.trim()) {
      const knownObject = JSON.parse(additionalConfig);
      message = {
        ...message,
        chatbot_config: {
          ...message.chatbot_config,
          ...knownObject,
        },
      };
    }

    console.info('send message:', message);
    sendMessage(JSON.stringify(message));

    // Only add to messages if it's a new message (not regeneration)
    if (!customQuery) {
      setMessages((prev) => {
        return [
          ...prev,
          {
            messageId: '',
            type: 'human',
            message: {
              data: messageToSend,
              monitoring: '',
            },
            attachments: selectedFiles,
          },
        ];
      });
      setSelectedFiles([]);
    }
  };

  useEffect(() => {
    if (modelType.value === 'Bedrock') {
      setModelList(LLM_BOT_COMMON_MODEL_LIST);
      setModelOption(LLM_BOT_COMMON_MODEL_LIST[0].options[0].value);
      setApiEndpoint('');
      setApiKeyArn('');
    } else if (modelType.value === 'Bedrock API') {
      setModelList(BR_API_MODEL_LIST);
      setModelOption(BR_API_MODEL_LIST[0].options[0].value);
    } else if (modelType.value === 'OpenAI API') {
      setModelList(OPENAI_API_MODEL_LIST);
      setModelOption(OPENAI_API_MODEL_LIST[0].options[0].value);
    } else if (modelType.value === 'siliconflow') {
      setModelList(SILICON_FLOW_API_MODEL_LIST);
      setModelOption(SILICON_FLOW_API_MODEL_LIST[0].options[0].value);
    } else if (modelType.value === 'SageMaker') {
      setModelList(SAGEMAKER_MODEL_LIST);
      setModelOption(SAGEMAKER_MODEL_LIST[0].options[0].value);
    } 
  }, [modelType]);

  useEffect(() => {
    if (modelOption === 'qwen2-72B-instruct') {
      setShowEndpoint(true);
    } else {
      setEndPoint('Qwen2-72B-Instruct-AWQ-2024-06-25-02-15-34-347');
      setShowEndpoint(false);
    }
  }, [modelOption]);

  const [feedbackGiven, setFeedbackGiven] = useState<{
    [key: string]: 'thumb_up' | 'thumb_down' | null;
  }>({});

  const handleThumbUpClick = async (index: number) => {
    const currentFeedback = feedbackGiven[index];
    const newFeedback = currentFeedback === 'thumb_up' ? null : 'thumb_up';

    try {
      await fetchData({
        url: `sessions/${sessionId}/messages/${messages[index].messageId}/feedback`,
        method: 'post',
        data: {
          feedback_type: newFeedback || '',
          feedback_reason: '',
          suggest_message: '',
        },
      });
      setFeedbackGiven((prev) => ({ ...prev, [index]: newFeedback }));
      console.log('Thumb up feedback sent successfully');
    } catch (error) {
      console.error('Error sending thumb up feedback:', error);
    }
  };

  const handleThumbDownClick = async (index: number) => {
    const currentFeedback = feedbackGiven[index];
    const newFeedback = currentFeedback === 'thumb_down' ? null : 'thumb_down';

    try {
      await fetchData({
        url: `sessions/${sessionId}/messages/${messages[index].messageId}/feedback`,
        method: 'post',
        data: {
          feedback_type: newFeedback || '',
          feedback_reason: '',
          suggest_message: '',
        },
      });
      setFeedbackGiven((prev) => ({ ...prev, [index]: newFeedback }));
      console.log('Thumb down feedback sent successfully');
    } catch (error) {
      console.error('Error sending thumb down feedback:', error);
    }
  };

  // Initialize showFigures from local storage
  const localShowFigures = localStorage.getItem(SHOW_FIGURES);
  const [showFigures, setShowFigures] = useState(
    localShowFigures === null || localShowFigures === 'true',
  );

  useEffect(() => {
    // Update local storage whenever showFigures changes
    localStorage.setItem('SHOW_FIGURES', showFigures ? 'true' : 'false');
  }, [showFigures]);

  const handleStopMessage = () => {
    const message = {
      message_type: 'STOP',
      session_id: sessionId,
      user_id: auth?.user?.profile?.['cognito:username'] || 'default_user_id',
    };

    console.info('Send stop message:', message);
    sendMessage(JSON.stringify(message));
  };

  // Update the render send button section
  const renderSendButton = () => {
    if (aiSpeaking) {
      return (
        <Button onClick={handleStopMessage} ariaLabel={t('button.stop')}>
          {t('button.stop')}
        </Button>
      );
    }

    return (
      <>
        <SpaceBetween direction='horizontal' size='xxs'>
          <div
            style={{ border: '2px solid #0972d3', borderRadius: 20, padding: 5, display: 'flex', alignItems: 'center', justifyContent: 'center', width: 20, height: 20 }}
            onClick={() => fileInputRef.current?.click()}
          >
            <img src={"/imgs/img-upload.png"} alt="attach" width={15}></img>
          </div>
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileChange}
            accept="image/*"
            multiple
          />
          <Button
            disabled={readyState !== ReadyState.OPEN}
            onClick={() => handleClickSendMessage()}
            ariaLabel={t('button.send')}
          >
            {t('button.send')}
          </Button></SpaceBetween>
      </>
    );
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      const newFiles = Array.from(event.target.files) as File[];
      setSelectedFiles((prevFiles) => [...prevFiles, ...newFiles]);
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
  };

  const handleRegenerateMessage = async (index: number) => {
    if (aiSpeaking) {
      return;
    }

    // Get the last human message before this AI message
    let humanMessage = '';
    for (let i = index - 1; i >= 0; i--) {
      if (messages[i].type === 'human') {
        humanMessage = messages[i].message.data;
        break;
      }
    }

    if (!humanMessage) {
      console.error('No human message found to regenerate response');
      return;
    }

    // Remove the AI message and all subsequent messages
    setMessages(messages.slice(0, index));

    // Reuse handleClickSendMessage with the found human message
    handleClickSendMessage(humanMessage);
  };

  return (
    <CommonLayout
      isLoading={loadingHistory}
      activeHref={!historySessionId ? ROUTES.Home : ROUTES.Session}
      breadCrumbs={[
        {
          text: t('name'),
          href: ROUTES.Home,
        },
        {
          text: t('conversation'),
          href: ROUTES.Chat,
        },
      ]}
    >
      <div className="chat-container-layout">
        <ContentLayout
          header={
            <Header
              variant="h1"
              actions={
                historySessionId ? (
                  <></>
                ) : (
                  <SpaceBetween size="xs" direction="horizontal">
                    <Button
                      variant="primary"
                      disabled={aiSpeaking || readyState !== ReadyState.OPEN}
                      onClick={() => {
                        startNewChat();
                      }}
                    >
                      {t('button.startNewChat')}
                    </Button>
                  </SpaceBetween>
                )
              }
              description={
                historySessionId
                  ? t('chatHistoryDescription') + ' ' + historySessionId
                  : t('chatDescription')
              }
            >
              <Box variant="h1">
                {historySessionId ? t('chatHistory') : t('chat')}
              </Box>
            </Header>
          }
        >
          {loadingChatBots ? (<Container
            fitHeight={true}>
            <div style={{ margin: "auto", textAlign: "center", marginTop: "30%" }}>
              <Spinner size="large" /></div>
          </Container>) : (
            <Container
              fitHeight={true}
              footer={
                <div>
                  <ExpandableSection
                    onChange={({ detail }) => {
                      setModelSettingExpand(detail.expanded);
                    }}
                    expanded={modelSettingExpand}
                    // variant="footer"
                    headingTagOverride="h4"
                    headerText={t('configurations')}
                  >
                    <div
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        marginBottom: 15,
                        marginTop: 15,
                      }}
                    >
                      {t('common')}
                    </div>
                    <SpaceBetween size="xs" direction="vertical">
                      <Grid gridDefinition={[{ colspan: 5 }, { colspan: 6 }]}>
                        <FormField
                          label={t('modelProvider')}
                          stretch={true}
                          description={t('scenarioDesc')}
                          // errorText={modelProviderHint}
                        >
                          <Select
                            options={MODEL_TYPE_LIST}
                            selectedOption={modelType}
                            onChange={({ detail }) => {
                              setModelType(detail.selectedOption);
                              setModelOption('');

                              // Check if the selected model provider matches the chatbot's model provider
                              // const selectedChatbotId =
                              //   chatbotOption.value ?? 'defaultId';
                              // const expectedModelProvider =
                              //   chatbotModelProvider[selectedChatbotId];

                              // if (
                              //   expectedModelProvider !==
                              //   detail.selectedOption.value &&
                              //   detail.selectedOption.value !== 'emd' &&
                              //   detail.selectedOption.value !== 'siliconflow'
                              // ) {
                              //   setModelProviderHint(
                              //     t('chatbotModelProviderError'),
                              //   );
                              // } else {
                              //   setModelProviderHint(''); // Clear hint if the selection is valid
                              // }
                            }}
                          />
                        </FormField>
                        {modelType.value === 'Bedrock API' ||
                          modelType.value === 'OpenAI API' ||
                          modelType.value === 'siliconflow' ? (
                          <SpaceBetween size="xs" direction="vertical">
                            <FormField
                              label={t('modelName')}
                              stretch={true}
                              errorText={t(modelError)}
                              description={t('modelNameDesc')}
                            >
                              <Autosuggest
                                onChange={({ detail }) => {
                                  setModelError('');
                                  setModelOption(detail.value);
                                }}
                                value={modelOption}
                                options={modelList}
                                enteredTextLabel={(value) => `Use: "${value}"`}
                                placeholder={t('validation.requireModel')}
                                empty={t('noModelFound')}
                              />
                            </FormField>
                            <FormField
                              label={t('apiEndpoint')}
                              stretch={true}
                              errorText={t(apiEndpointError)}
                              description={t('apiEndpointDesc')}
                            >
                              <Input
                                value={apiEndpoint}
                                onChange={({ detail }) => {
                                  const value = detail.value;
                                  if (value === '' || isValidUrl(value)) {
                                    setApiEndpointError('');
                                  } else {
                                    setApiEndpointError(
                                      'Invalid url, please type in a valid HTTPS or HTTP url',
                                    );
                                  }
                                  setApiEndpoint(value);
                                }}
                                placeholder="https://api.example.com/v1"
                              />
                            </FormField>
                            <FormField
                              label={t('apiKeyArn')}
                              stretch={true}
                              errorText={t(apiKeyArnError)}
                              description={t('apiKeyArnDesc')}
                            >
                              <Input
                                value={apiKeyArn}
                                onChange={({ detail }) => {
                                  const value = detail.value;
                                  if (value === '' || isValidArn(value)) {
                                    setApiKeyArnError('');
                                  } else {
                                    setApiKeyArnError(
                                      'Invalid ARN, please type in a valid secret ARN from AWS Secrets Manager',
                                    );
                                  }
                                  setApiKeyArn(value);
                                }}
                                placeholder="arn:aws:secretsmanager:region:account:secret:name"
                              />
                            </FormField>
                          </SpaceBetween>
                        ) : (<>
                          
                          {modelType.value === 'SageMaker' ? (
                             <SpaceBetween size="xs" direction="vertical">
                            <FormField
                            label={t('modelName')}
                            stretch={true}
                            errorText={t(modelError)}
                            description={t('modelNameDesc')}
                          >
                            <Autosuggest
                              onChange={({ detail }) => {
                                setModelError('');
                                setModelOption(detail.value);
                              }}
                              value={modelOption}
                              options={modelList}
                              placeholder={t('validation.requireModel')}
                              empty={t('noModelFound')}
                              enteredTextLabel={(value) => `Use: "${value}"`}
                            />
                          </FormField>
                            <FormField
                            label={t('sagemakerEndpoint')}
                            stretch={true}
                            errorText={t(apiEndpointError)}
                            description={t('sagemakerEndpointDesc')}
                          >
                            <Select

                    onChange={({ detail }: { detail: any }) => {
                      setApiEndpointError('');
                      setApiEndpoint(detail.selectedOption.value);
                      setApiEndpointOption(detail.selectedOption);
                    }}
                    loadingText={t('loadingEp')}
                    selectedOption={apiEndpointOption}
                    options={endpoints}
                    placeholder={t('validation.requireModel')}
                    empty={t('noModelFound')}
                  />
                          </FormField></SpaceBetween>
                          ):(
                            <FormField
                            label={t('modelName')}
                            stretch={true}
                            errorText={t(modelError)}
                            description={t('modelNameDesc')}
                          >
                            <Autosuggest
                              onChange={({ detail }) => {
                                setModelError('');
                                setModelOption(detail.value);
                              }}
                              value={modelOption}
                              options={modelList}
                              placeholder={t('validation.requireModel')}
                              empty={t('noModelFound')}
                              enteredTextLabel={(value) => `Use: "${value}"`}
                            />
                          </FormField>
                          )


                          }</>
                        )}
                      </Grid>
                      <Grid gridDefinition={[{ colspan: 5 }, { colspan: 6 }]}>
                        <FormField
                          label={t('maxTokens')}
                          stretch={true}
                          errorText={t(maxTokenError)}
                          description={t('maxTokenDesc')}
                        >
                          <Input
                            type="number"
                            value={maxToken}
                            onChange={({ detail }) => {
                              setMaxTokenError('');
                              setMaxToken(detail.value);
                            }}
                          />
                        </FormField>
                        <FormField
                          label={t('maxRounds')}
                          stretch={true}
                          errorText={t(maxRoundsError)}
                          description={t('maxRoundsDesc')}
                        >
                          <Input
                            type="number"
                            value={maxRounds}
                            onChange={({ detail }) => {
                              if (
                                parseInt(detail.value) < 0 ||
                                parseInt(detail.value) > 100
                              ) {
                                return;
                              }
                              setMaxRoundsError('');
                              setMaxRounds(detail.value);
                            }}
                          />
                        </FormField>
                      </Grid>

                      {showEndpoint && (
                        <Grid gridDefinition={[{ colspan: 11 }]}>
                          <FormField
                            label={t('endPoint')}
                            stretch={true}
                            errorText={t(endPointError)}
                            description={t('endPointDesc')}
                          >
                            <Input
                              onChange={({ detail }) => {
                                setEndPointError('');
                                setEndPoint(detail.value);
                              }}
                              value={endPoint}
                              placeholder="QWen2-72B-XXXXX"
                            />
                          </FormField>
                        </Grid>
                      )}
                    </SpaceBetween>
                    <div
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        marginBottom: 15,
                        marginTop: 35,
                      }}
                    >
                      {t('rad')}
                    </div>
                    <SpaceBetween size="xs" direction="vertical">
                      <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                        <FormField
                          label={t('recallByKeyword')}
                          stretch={true}
                          description={t('recallByKeywordDesc')}
                        >
                          <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                            <FormField
                              stretch={true}
                              description={t('topK')}
                              errorText={topKKeywordError}
                            >
                              <Input
                                type="number"
                                value={topKKeyword}
                                onChange={({ detail }) => {
                                  if (
                                    parseInt(detail.value) < 1 ||
                                    parseInt(detail.value) > 100
                                  ) {
                                    return;
                                  }
                                  setTopKKeywordError('');
                                  setTopKKeyword(detail.value);
                                }}
                              />
                            </FormField>
                            <FormField
                              stretch={true}
                              description={t('threshold')}
                              errorText={keywordScoreError}
                            >
                              <Input
                                type="number"
                                step={0.01}
                                value={keywordScore}
                                onChange={({ detail }) => {
                                  if (
                                    parseFloat(detail.value) < 0 ||
                                    parseFloat(detail.value) > 1
                                  ) {
                                    return;
                                  }
                                  setKeywordScoreError('');
                                  setKeywordScore(detail.value);
                                }}
                              />
                            </FormField>
                          </Grid>
                        </FormField>
                        <FormField
                          label={t('recallByEmbedding')}
                          stretch={true}
                          description={t('recallByEmbeddingDesc')}
                        >
                          <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                            <FormField
                              stretch={true}
                              description={t('topK')}
                              errorText={topKEmbeddingError}
                            >
                              <Input
                                type="number"
                                value={topKEmbedding}
                                onChange={({ detail }) => {
                                  if (
                                    parseInt(detail.value) < 1 ||
                                    parseInt(detail.value) > 100
                                  ) {
                                    return;
                                  }
                                  setTopKEmbeddingError('');
                                  setTopKEmbedding(detail.value);
                                }}
                              />
                            </FormField>
                            <FormField
                              stretch={true}
                              description={t('threshold')}
                              errorText={embeddingScoreError}
                            >
                              <Input
                                type="number"
                                step={0.01}
                                value={embeddingScore}
                                onChange={({ detail }) => {
                                  if (
                                    parseFloat(detail.value) < 0 ||
                                    parseFloat(detail.value) > 1
                                  ) {
                                    return;
                                  }
                                  setEmbeddingScoreError('');
                                  setEmbeddingScore(detail.value);
                                }}
                              />
                            </FormField>
                          </Grid>
                        </FormField>
                      </Grid>

                      {/* <FormField
                        label={t('topKRetrievals')}
                        stretch={true}
                        description={t('topKRetrievalsDesc')}
                        errorText={t(topKRetrievalsError)}
                      >
                        <Input
                          type="number"
                          value={topKRetrievals}
                          onChange={({ detail }) => {
                            if (
                              parseInt(detail.value) < 0 ||
                              parseInt(detail.value) > 100
                            ) {
                              return;
                            }
                            setTopKRetrievalsError('');
                            setTopKRetrievals(detail.value);
                          }}
                        />
                      </FormField> */}
                      {/* <FormField
                        label={t('score')}
                        stretch={true}
                        description={t('scoreDesc')}
                        errorText={t(scoreError)}
                      >
                        <Input
                          type="number"
                          step={0.01}
                          value={score}
                          onChange={({ detail }) => {
                            if (
                              parseFloat(detail.value) < 0 ||
                              parseFloat(detail.value) > 1
                            ) {
                              return;
                            }
                            setScoreError('');
                            setScore(detail.value);
                          }}
                        />
                      </FormField>
                    </Grid> */}
                      <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                        {/* <FormField
                        label={t('topKKeyword')}
                        stretch={true}
                        description={t('topKKeywordDesc')}
                        errorText={t(topKKeywordError)}
                      >
                        <Input
                          type="number"
                          value={topKKeyword}
                          onChange={({ detail }) => {
                            if (parseInt(detail.value) < 0 || parseInt(detail.value) > 100) {
                              return
                            }
                            setTopKKeywordError('');
                            setTopKKeyword(detail.value);
                          }}
                        />
                      </FormField>
                      
                      <FormField
                        label={t('topKEmbedding')}
                        stretch={true}
                        description={t('topKEmbeddingDesc')}
                        errorText={t(topKEmbeddingError)}
                      >
                        <Input
                          type="number"
                          value={topKEmbedding}
                          onChange={({ detail }) => {
                            if (parseInt(detail.value) < 0 || parseInt(detail.value) > 100) {
                              return
                            }
                            setTopKEmbeddingError('');
                            setTopKEmbedding(detail.value);
                          }}
                        />
                      </FormField> */}

                        <FormField
                          label={t('topKRerank')}
                          stretch={true}
                          description={t('topKRerankDesc')}
                          errorText={t(topKRerankError)}
                        >
                          <Input
                            type="number"
                            value={topKRerank}
                            onChange={({ detail }) => {
                              if (
                                parseInt(detail.value) < 0 ||
                                parseInt(detail.value) > 100
                              ) {
                                return;
                              }
                              setTopKRerankError('');
                              setTopKRerank(detail.value);
                            }}
                          />
                        </FormField>
                        <FormField
                          label={t('temperature')}
                          stretch={true}
                          errorText={t(temperatureError)}
                          description={t('temperatureDesc')}
                        >
                          <Input
                            type="number"
                            step={0.01}
                            value={temperature}
                            onChange={({ detail }) => {
                              if (
                                parseFloat(detail.value) < 0 ||
                                parseFloat(detail.value) > 1
                              ) {
                                return;
                              }
                              setTemperatureError('');
                              setTemperature(detail.value);
                            }}
                          />
                        </FormField>
                      </Grid>
                      <FormField
                        label={t('additionalSettings')}
                        errorText={t(additionalConfigError)}
                      >
                        <Textarea
                          rows={7}
                          value={additionalConfig}
                          onChange={({ detail }) => {
                            setAdditionalConfigError('');
                            setAdditionalConfig(detail.value);
                          }}
                          placeholder={JSON.stringify(
                            {
                              key: 'value',
                              key2: ['value1', 'value2'],
                            },
                            null,
                            4,
                          )}
                        />
                      </FormField>
                    </SpaceBetween>
                  </ExpandableSection>
                </div>
              }
            >
              <div className="chat-container mt-10">
                <div className="chat-message flex-v flex-1 gap-10">
                  {messages.map((msg, index) => (
                    <div key={identity(index)}>
                      <Message
                        showTrace={showTrace}
                        type={msg.type}
                        message={msg.message}
                      />
                      {msg.type === 'ai' && index !== 0 && (
                        <div
                          className="feedback-buttons"
                          style={{
                            display: 'flex',
                            justifyContent: 'flex-end',
                            gap: '8px',
                          }}
                        >
                          <Button
                            iconName="refresh"
                            variant="icon"
                            disabled={aiSpeaking}
                            onClick={() => handleRegenerateMessage(index)}
                            ariaLabel={t('regenerate')}
                          />
                          <Button
                            iconName={
                              feedbackGiven[index] === 'thumb_up'
                                ? 'thumbs-up-filled'
                                : 'thumbs-up'
                            }
                            variant="icon"
                            onClick={() => handleThumbUpClick(index)}
                            ariaLabel={t('feedback.helpful')}
                          />
                          <Button
                            iconName={
                              feedbackGiven[index] === 'thumb_down'
                                ? 'thumbs-down-filled'
                                : 'thumbs-down'
                            }
                            variant="icon"
                            onClick={() => handleThumbDownClick(index)}
                            ariaLabel={t('feedback.notHelpful')}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                  {aiSpeaking && (
                    <div>
                      <Message
                        aiSpeaking={aiSpeaking}
                        type="ai"
                        showTrace={showTrace}
                        message={{
                          data: currentAIMessage,
                          monitoring: currentMonitorMessage,
                        }}
                      />
                      {isMessageEnd && (
                        <div
                          className="feedback-buttons"
                          style={{
                            display: 'flex',
                            justifyContent: 'flex-end',
                            gap: '8px',
                          }}
                        >
                          <Button
                            iconName="refresh"
                            variant="icon"
                            disabled={aiSpeaking}
                            onClick={() =>
                              handleRegenerateMessage(messages.length)
                            }
                            ariaLabel={t('regenerate')}
                          />
                          <Button
                            iconName={
                              feedbackGiven[messages.length] === 'thumb_up'
                                ? 'thumbs-up-filled'
                                : 'thumbs-up'
                            }
                            variant="icon"
                            onClick={() => handleThumbUpClick(messages.length)}
                            ariaLabel={t('feedback.helpful')}
                          />
                          <Button
                            iconName={
                              feedbackGiven[messages.length] === 'thumb_down'
                                ? 'thumbs-down-filled'
                                : 'thumbs-down'
                            }
                            variant="icon"
                            onClick={() => handleThumbDownClick(messages.length)}
                            ariaLabel={t('feedback.notHelpful')}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex-v gap-10">
                  {selectedFiles.length > 0 && (
                    <div className="image-preview">
                      {selectedFiles.map((file, index) => (
                        <div
                          key={index}
                          style={{
                            position: 'relative',
                            display: 'inline-block',
                            marginRight: '10px',
                          }}
                        >
                          <img
                            src={URL.createObjectURL(file)}
                            alt={`Preview ${index + 1}`}
                            style={{ maxWidth: '100px', maxHeight: '100px' }}
                          />
                          <Button
                            iconName="close"
                            variant="icon"
                            onClick={() => handleRemoveFile(index)}
                            ariaLabel={t('button.removeImage')}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-5 send-message">
                    <Select
                      options={chatbotList}
                      loadingText="loading..."
                      selectedOption={chatbotOption}
                      onChange={({ detail }) => {
                        setChatbotOption(detail.selectedOption);
                        // Remove history chatbot ID from localStorage when manually changing chatbot
                        // Next time it will only use current_chatbot in localStorage
                        localStorage.removeItem(HISTORY_CHATBOT_ID);
                      }}
                    />
                    <div className="flex-1 pr">
                      <Textarea
                        invalid={showMessageError}
                        rows={1}
                        value={userMessage}
                        placeholder={t('typeMessage')}
                        onChange={(e) => {
                          setShowMessageError(false);
                          setUserMessage(e.detail.value);
                        }}
                        onKeyDown={(e) => {
                          if (e.detail.key === 'Enter' && !isComposing) {
                            e.preventDefault();
                            handleClickSendMessage();
                          }
                        }}
                      />
                    </div>
                    <div>{renderSendButton()}</div>
                  </div>
                  <div>
                    <div className="flex space-between">
                      <div className="flex gap-10 align-center">
                        <Toggle
                          onChange={({ detail }) =>
                            setUseChatHistory(detail.checked)
                          }
                          checked={useChatHistory}
                        >
                          {t('multiRound')}
                        </Toggle>
                        <Toggle
                          onChange={({ detail }) =>
                            setEnableTrace(detail.checked)
                          }
                          checked={enableTrace}
                        >
                          {t('enableTrace')}
                        </Toggle>
                        <Toggle
                          onChange={({ detail }) =>
                            setShowFigures(detail.checked)
                          }
                          checked={showFigures}
                        >
                          {t('showFigures')}
                        </Toggle>
                        <Toggle
                          onChange={({ detail }) =>
                            setOnlyRAGTool(detail.checked)
                          }
                          checked={onlyRAGTool}
                        >
                          {t('onlyUseRAGTool')}
                        </Toggle>
                      </div>
                      <div className="flex align-center gap-10">
                        <Box variant="p">{t('server')}: </Box>
                        <StatusIndicator type={connectionStatus as any}>
                          {t(connectionStatus)}
                        </StatusIndicator>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Container>
          )}

        </ContentLayout>
      </div>
    </CommonLayout>
  );
};

export default ChatBot;
