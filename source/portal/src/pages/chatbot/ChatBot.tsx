import React, { useContext, useEffect, useState } from 'react';
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
  StatusIndicator,
  Textarea,
  Toggle,
} from '@cloudscape-design/components';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { identity } from 'lodash';
import ConfigContext from 'src/context/config-context';
import { useAuth } from 'react-oidc-context';
import {
  LLM_BOT_COMMON_MODEL_LIST,
  LLM_BOT_RETAIL_MODEL_LIST,
  SCENARIO_LIST,
  RETAIL_GOODS_LIST,
  SCENARIO,
  MAX_TOKEN,
  TEMPERATURE,
  ADITIONAL_SETTINGS,
  USE_CHAT_HISTORY,
  ENABLE_TRACE,
  ONLY_RAG_TOOL,
  MODEL_OPTION,
  CURRENT_CHAT_BOT,
  TOPK,
  SCORE,
  ROUND,
  HISTORY_CHATBOT_ID,
} from 'src/utils/const';
import { v4 as uuidv4 } from 'uuid';
import { MessageDataType, SessionMessage } from 'src/types';
import { isValidJson } from 'src/utils/utils';

interface MessageType {
  messageId: string;
  type: 'ai' | 'human';
  message: {
    data: string;
    monitoring: string;
  };
}

interface ChatBotProps {
  historySessionId?: string;
}

const ChatBot: React.FC<ChatBotProps> = (props: ChatBotProps) => {
  const { historySessionId } = props;
  const localScenario = localStorage.getItem(SCENARIO);
  const localMaxToken = localStorage.getItem(MAX_TOKEN);
  const localTemperature = localStorage.getItem(TEMPERATURE);
  const localConfig = localStorage.getItem(ADITIONAL_SETTINGS);
  const localRound = localStorage.getItem(ROUND);
  const localTopKRetrievals = localStorage.getItem(TOPK);
  const localScore = localStorage.getItem(SCORE);
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
  const { lastMessage, sendMessage, readyState } = useWebSocket(
    `${config?.websocket}?idToken=${auth.user?.id_token}`,
    {
      onOpen: () => console.log('opened'),
      shouldReconnect: () => true,
    },
  );
  const [currentAIMessage, setCurrentAIMessage] = useState('');
  const [currentMonitorMessage, setCurrentMonitorMessage] = useState('');
  const [currentAIMessageId, setCurrentAIMessageId] = useState('');
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [modelOption, setModelOption] = useState('');
  const [modelList, setModelList] = useState<SelectProps.Option[]>([]);
  const [chatbotList, setChatbotList] = useState<SelectProps.Option[]>([]);
  const [chatbotOption, setChatbotOption] = useState<SelectProps.Option>(
    null as any,
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
  // const [useWebSearch, setUseWebSearch] = useState(false);
  // const [googleAPIKey, setGoogleAPIKey] = useState('');
  const [retailGoods, setRetailGoods] = useState<SelectProps.Option>(
    RETAIL_GOODS_LIST[0],
  );
  const [scenario, setScenario] = useState<SelectProps.Option>(
    localScenario == null ? SCENARIO_LIST[0] : JSON.parse(localScenario),
  );
  const defaultConfig = {
    temperature: '0.01',
    maxToken: '1000',
    maxRounds: '7',
    topKRetrievals: '5',
    score: '0.4',
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
  const [topKRetrievals, setTopKRetrievals] = useState<string>(
    localTopKRetrievals ?? defaultConfig.topKRetrievals,
  );
  const [score, setScore] = useState<string>(localScore ?? defaultConfig.score);
  const [additionalConfig, setAdditionalConfig] = useState(
    localConfig ?? defaultConfig.additionalConfig,
  );
  const [topKRetrievalsError, setTopKRetrievalsError] = useState('');
  const [maxRoundsError, setMaxRoundsError] = useState('');
  const [scoreError, setScoreError] = useState('');

  const [endPoint, setEndPoint] = useState('');
  const [showEndpoint, setShowEndpoint] = useState(false);
  const [endPointError, setEndPointError] = useState('');
  const [showMessageError, setShowMessageError] = useState(false);
  const [isMessageEnd, setIsMessageEnd] = useState(false);

  // validation
  const [modelError, setModelError] = useState('');
  const [temperatureError, setTemperatureError] = useState('');
  const [maxTokenError, setMaxTokenError] = useState('');
  const [modelSettingExpand, setModelSettingExpand] = useState(false);
  const [additionalConfigError, setAdditionalConfigError] = useState('');

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'loading',
    [ReadyState.OPEN]: 'success',
    [ReadyState.CLOSING]: 'closing',
    [ReadyState.CLOSED]: 'error',
    [ReadyState.UNINSTANTIATED]: 'pending',
  }[readyState];

  // Define an async function to get the data
  const fetchData = useAxiosRequest();

  const startNewChat = () => {
    [
      CURRENT_CHAT_BOT,
      ENABLE_TRACE,
      MAX_TOKEN,
      MODEL_OPTION,
      ONLY_RAG_TOOL,
      SCENARIO,
      TEMPERATURE,
      USE_CHAT_HISTORY,
    ].forEach((item) => {
      localStorage.removeItem(item);
    });
    // localStorage.()
    setChatbotOption(chatbotList[0])
    setScenario(SCENARIO_LIST[0])
    setMaxToken(defaultConfig.maxToken)
    setMaxRounds(defaultConfig.maxRounds)
    setTemperature(defaultConfig.temperature)
    setTopKRetrievals(defaultConfig.topKRetrievals)
    setScore(defaultConfig.score)
    setUserMessage('')
    setAdditionalConfig('')
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
      const chatbots: string[] = data.chatbot_ids;
      const getChatbots = chatbots.map((item) => {
        return {
          label: item,
          value: item,
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
      if (historySessionId) {
        // Wait for getSessionHistoryById to complete to set history chatbotId
        await getSessionHistoryById();
      } else {
        setSessionId(uuidv4());
      }
      // Call getWorkspaceList after getSessionHistoryById
      getWorkspaceList();
    };

    initializeChatbot();
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
    if (scenario) {
      localStorage.setItem(SCENARIO, JSON.stringify(scenario));
    }
  }, [scenario]);

  useEffect(() => {
    if (maxRounds) {
      localStorage.setItem(ROUND, maxRounds);
    }
  }, [maxRounds]);

  useEffect(() => {
    if (topKRetrievals) {
      localStorage.setItem(TOPK, topKRetrievals);
    }
  }, [topKRetrievals]);

  useEffect(() => {
    if (score) {
      localStorage.setItem(SCORE, score);
    }
  }, [score]);

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

  const handleAIMessage = (message: MessageDataType) => {
    console.info('handleAIMessage:', message);
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
      setCurrentAIMessageId(message.message_id);
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

  const handleClickSendMessage = () => {
    if (aiSpeaking) {
      return;
    }
    if (!userMessage.trim()) {
      setShowMessageError(true);
      return;
    }
    // validate websocket status
    if (readyState !== ReadyState.OPEN) {
      return;
    }
    // validate model settings
    if (!modelOption.trim()) {
      setModelError('validation.requireModel');
      setModelSettingExpand(true);
      return;
    }
    if (!temperature.trim()) {
      setTemperatureError('validation.requireTemperature');
      setModelSettingExpand(true);
      return;
    }
    if (!maxToken.trim()) {
      setMaxTokenError('validation.requireMaxTokens');
      setModelSettingExpand(true);
      return;
    }
    if (parseInt(maxToken) < 1) {
      setMaxTokenError('validation.maxTokensRange');
      setModelSettingExpand(true);
      return;
    }

    if (!maxRounds.trim()) {
      setMaxRoundsError('validation.requireMaxRounds');
      setModelSettingExpand(true);
      return;
    }

    if (parseInt(maxRounds) < 0) {
      setMaxRoundsError('validation.maxRoundsRange');
      setModelSettingExpand(true);
      return;
    }

    if (!topKRetrievals.trim()) {
      setTopKRetrievalsError('validation.requireTopKRetrievals');
      setModelSettingExpand(true);
      return;
    }

    if (parseInt(topKRetrievals) < 1) {
      setTopKRetrievalsError('validation.topKRetrievals');
      setModelSettingExpand(true);
      return;
    }

    if (parseFloat(temperature) < 0.0 || parseFloat(temperature) > 1.0) {
      setTemperatureError('validation.temperatureRange');
      setModelSettingExpand(true);
      return;
    }

    if (!score.trim()) {
      setScoreError('validation.requireScore');
      setModelSettingExpand(true);
      return;
    }

    if (parseFloat(score) < 0.0 || parseFloat(score) > 1.0) {
      setScoreError('validation.score');
      setModelSettingExpand(true);
      return;
    }
    // validate endpoint
    if (modelOption === 'qwen2-72B-instruct' && !endPoint.trim()) {
      setEndPointError('validation.requireEndPoint');
      setModelSettingExpand(true);
      return;
    }

    // validate additional config
    if (additionalConfig.trim() && !isValidJson(additionalConfig)) {
      setAdditionalConfigError('validation.invalidJson');
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
      query: userMessage,
      entry_type: scenario.value,
      session_id: sessionId,
      user_id: auth?.user?.profile?.['cognito:username'] || 'default_user_id',
      chatbot_config: {
        max_rounds_in_memory: parseInt(maxRounds),
        group_name: groupName?.[0] ?? 'Admin',
        chatbot_id: chatbotOption.value ?? 'admin',
        goods_id: retailGoods.value,
        chatbot_mode: 'agent',
        use_history: useChatHistory,
        enable_trace: enableTrace,
        use_websearch: true,
        google_api_key: '',
        default_llm_config: {
          model_id: modelOption,
          endpoint_name:
            modelOption === 'qwen2-72B-instruct' ? endPoint.trim() : '',
          model_kwargs: {
            temperature: parseFloat(temperature),
            max_tokens: parseInt(maxToken),
          },
        },
        private_knowledge_config: {
          top_k: parseInt(topKRetrievals),
          score: parseFloat(score),
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
    setMessages((prev) => {
      return [
        ...prev,
        {
          messageId: '',
          type: 'human',
          message: {
            data: userMessage,
            monitoring: '',
          },
        },
      ];
    });
    setUserMessage('');
  };

  useEffect(() => {
    let optionList: any[] = [];
    const localModel = localStorage.getItem(MODEL_OPTION);
    if (scenario.value === 'common') {
      optionList = LLM_BOT_COMMON_MODEL_LIST;
      setModelList(LLM_BOT_COMMON_MODEL_LIST);
    } else if (scenario.value === 'retail') {
      optionList = LLM_BOT_RETAIL_MODEL_LIST;
      setModelList(LLM_BOT_RETAIL_MODEL_LIST);
    }
    if (localModel) {
      setModelOption(localModel);
    } else {
      setModelOption(optionList?.[0]?.options?.[0].value ?? '');
    }
  }, [scenario]);

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
  const localShowFigures = localStorage.getItem('SHOW_FIGURES');
  const [showFigures, setShowFigures] = useState(
    localShowFigures === null || localShowFigures === 'true',
  );

  useEffect(() => {
    // Update local storage whenever showFigures changes
    localStorage.setItem('SHOW_FIGURES', showFigures ? 'true' : 'false');
  }, [showFigures]);

  return (
    <CommonLayout
      isLoading={loadingHistory}
      activeHref={!historySessionId ? '/' : '/sessions'}
      breadCrumbs={[
        {
          text: t('name'),
          href: '/',
        },
        {
          text: t('conversation'),
          href: '/chats',
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
                  {/* <SpaceBetween direction="vertical" size="l"> */}
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
                      {/* <ColumnLayout columns={3} variant="text-grid"> */}
                      <FormField
                        label={t('scenario')}
                        stretch={true}
                        description={t('scenarioDesc')}
                      >
                        <Select
                          options={SCENARIO_LIST}
                          selectedOption={scenario}
                          onChange={({ detail }) => {
                            setScenario(detail.selectedOption);
                          }}
                        />
                        {scenario.value == 'retail' && (
                          <div style={{ minWidth: 300 }}>
                            <Select
                              options={RETAIL_GOODS_LIST}
                              selectedOption={retailGoods}
                              onChange={({ detail }) => {
                                setRetailGoods(detail.selectedOption);
                              }}
                            />
                          </div>
                        )}
                      </FormField>
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
                        />
                      </FormField>
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
                    <Grid
                      gridDefinition={[
                        { colspan: 3 },
                        { colspan: 3 },
                        { colspan: 5 },
                      ]}
                    >
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
                      <FormField
                        label={t('topKRetrievals')}
                        stretch={true}
                        description={t('topKRetrievalsDesc')}
                        errorText={t(topKRetrievalsError)}
                      >
                        <Input
                          type="number"
                          value={topKRetrievals}
                          onChange={({ detail }) => {
                            setTopKRetrievalsError('');
                            setTopKRetrievals(detail.value);
                          }}
                        />
                      </FormField>
                      <FormField
                        label={t('score')}
                        stretch={true}
                        description={t('scoreDesc')}
                        errorText={t(scoreError)}
                      >
                        <Input
                          type="number"
                          step={0.1}
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
                    </Grid>
                    <Grid gridDefinition={[ {colspan: 5},{colspan: 6}]}>
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
                        if(parseInt(detail.value) < 0 || parseInt(detail.value) > 100){
                          return
                        }
                        setMaxRoundsError('');
                        setMaxRounds(detail.value);
                      }}
                    />
                  </FormField>
                  </Grid>
                  
                  {showEndpoint && (
                    <Grid gridDefinition={[{colspan: 11}]}>
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
                    </Grid>
                    )
                  }
                  
                </SpaceBetween>
                  <div style={{fontSize: 16, fontWeight: 700,marginBottom: 15, marginTop: 35}}>{t('rad')}</div>
                  <SpaceBetween size="xs" direction="vertical">
                    <Grid gridDefinition={[{colspan: 3},{colspan: 3},{colspan: 5}]}>
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
                        if(parseFloat(detail.value) < 0 || parseFloat(detail.value) > 1){
                          return
                        }
                        setTemperatureError('');
                        setTemperature(detail.value);
                      }}
                    />
                  </FormField>
                  <FormField
                    label={t('topKRetrievals')}
                    stretch={true}
                    description={t('topKRetrievalsDesc')}
                    errorText={t(topKRetrievalsError)}
                  >
                    <Input
                      type="number"
                      value={topKRetrievals}
                      onChange={({ detail }) => {
                        if(parseInt(detail.value) < 0 || parseInt(detail.value) > 100){
                          return
                        }
                        setTopKRetrievalsError('');
                        setTopKRetrievals(detail.value);
                      }}
                    />
                  </FormField>
                  <FormField
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
                        if(parseFloat(detail.value) < 0 || parseFloat(detail.value) > 1){
                          return
                        }
                        setScoreError('');
                        setScore(detail.value);
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

              {/* {historySessionId?(<></>): */}
              {/* ( */}
              <div className="flex-v gap-10">
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
                  <div>
                    <Button
                      disabled={aiSpeaking || readyState !== ReadyState.OPEN}
                      onClick={() => {
                        handleClickSendMessage();
                      }}
                    >
                      {t('button.send')}
                    </Button>
                  </div>
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
              {/* )} */}
            </div>
          </Container>
        </ContentLayout>
      </div>
    </CommonLayout>
  );
};

export default ChatBot;
