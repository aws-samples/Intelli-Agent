import React, { useContext, useEffect, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import Message from './components/Message';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import {
  Autosuggest,
  Box,
  Button,
  ColumnLayout,
  ExpandableSection,
  FormField,
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
  LLM_BOT_CHAT_MODE_LIST,
  LLM_BOT_COMMON_MODEL_LIST,
  LLM_BOT_RETAIL_MODEL_LIST,
  SCENARIO_LIST,
  RETAIL_GOODS_LIST,
} from 'src/utils/const';
import { v4 as uuidv4 } from 'uuid';
import { MessageDataType, SessionMessage } from 'src/types';

interface MessageType {
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
  const config = useContext(ConfigContext);
  const { t } = useTranslation();
  const auth = useAuth();
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [messages, setMessages] = useState<MessageType[]>([
    {
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
      //Will attempt to reconnect on all close events, such as server shutting down
      shouldReconnect: () => true,
    },
  );
  const [currentAIMessage, setCurrentAIMessage] = useState('');
  const [currentMonitorMessage, setCurrentMonitorMessage] = useState('');
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [modelOption, setModelOption] = useState('');
  const [modelList, setModelList] = useState<SelectProps.Option[]>([]);
  const [chatModeOption, setChatModeOption] = useState<SelectProps.Option>(
    LLM_BOT_CHAT_MODE_LIST[0],
  );
  const [useChatHistory, setUseChatHistory] = useState(true);
  const [enableTrace, setEnableTrace] = useState(true);
  const [showTrace, setShowTrace] = useState(true);
  // const [useWebSearch, setUseWebSearch] = useState(false);
  // const [googleAPIKey, setGoogleAPIKey] = useState('');
  const [retailGoods, setRetailGoods] = useState<SelectProps.Option>(
    RETAIL_GOODS_LIST[0],
  );
  const [scenario, setScenario] = useState<SelectProps.Option>(
    SCENARIO_LIST[0],
  );

  const [sessionId, setSessionId] = useState(historySessionId);
  const [workspaceIds, setWorkspaceIds] = useState<any[]>([]);

  const [temperature, setTemperature] = useState<string>('0.01');
  const [maxToken, setMaxToken] = useState<string>('1000');

  const [endPoint, setEndPoint] = useState('');
  const [showEndpoint, setShowEndpoint] = useState(false);
  const [endPointError, setEndPointError] = useState('');
  const [showMessageError, setShowMessageError] = useState(false);
  // const [googleAPIKeyError, setGoogleAPIKeyError] = useState(false);
  const [isMessageEnd, setIsMessageEnd] = useState(false);

  // validation
  const [modelError, setModelError] = useState('');
  const [temperatureError, setTemperatureError] = useState('');
  const [maxTokenError, setMaxTokenError] = useState('');
  const [modelSettingExpand, setModelSettingExpand] = useState(false);

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'loading',
    [ReadyState.OPEN]: 'success',
    [ReadyState.CLOSING]: 'closing',
    [ReadyState.CLOSED]: 'error',
    [ReadyState.UNINSTANTIATED]: 'pending',
  }[readyState];

  // Define an async function to get the data
  const fetchData = useAxiosRequest();

  const getWorkspaceList = async () => {
    try {
      const data = await fetchData({
        url: 'etl/list-workspace',
        method: 'get',
      });
      setWorkspaceIds(data.workspace_ids);
    } catch (error) {
      console.error(error);
      return [];
    }
  };

  const getSessionHistoryById = async () => {
    try {
      setLoadingHistory(true);
      const data = await fetchData({
        url: `ddb/list-messages`,
        method: 'get',
        params: {
          session_id: historySessionId,
          page_size: 9999,
          max_items: 9999,
        },
      });
      const sessionMessage: SessionMessage[] = data.Items;
      setMessages(
        sessionMessage.map((msg) => {
          return {
            type: msg.role,
            message: {
              data: msg.content,
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
    if (historySessionId) {
      // get session history by id
      getSessionHistoryById();
    } else {
      setSessionId(uuidv4());
    }
    getWorkspaceList();
  }, []);

  useEffect(() => {
    if (enableTrace) {
      setShowTrace(true);
    } else {
      setShowTrace(false);
    }
  }, [enableTrace]);

  const handleAIMessage = (message: MessageDataType) => {
    console.info('handleAIMessage:', message);
    if (message.message_type === 'START') {
      console.info('message started');
    } else if (message.message_type === 'CHUNK') {
      setCurrentAIMessage((prev) => {
        return prev + (message?.message?.content ?? '');
      });
    } else if (message.message_type === 'END') {
      setIsMessageEnd(true);
    }
  };

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
    if (parseFloat(temperature) < 0.0 || parseFloat(temperature) > 1.0) {
      setTemperatureError('validation.temperatureRange');
      setModelSettingExpand(true);
      return;
    }
    // validate endpoint
    if (modelOption === 'qwen2-72B-instruct' && !endPoint.trim()) {
      setEndPointError('validation.requireEndPoint');
      setModelSettingExpand(true);
      return;
    }

    setUserMessage('');
    setAiSpeaking(true);
    setCurrentAIMessage('');
    setCurrentMonitorMessage('');
    setIsMessageEnd(false);
    // if (useWebSearch && !googleAPIKey.trim()) {
    //   setGoogleAPIKeyError(true);
    //   return;
    // }
    const message = {
      query: userMessage,
      entry_type: scenario.value,
      session_id: sessionId,
      chatbot_config: {
        goods_id: retailGoods.value,
        chatbot_mode: chatModeOption.value,
        use_history: useChatHistory,
        enable_trace: enableTrace,
        use_websearch: true,
        google_api_key: '',
        default_workspace_config: {
          rag_workspace_ids: workspaceIds,
        },
        default_llm_config: {
          model_id: modelOption,
          endpoint_name:
            modelOption === 'qwen2-72B-instruct' ? endPoint.trim() : '',
          model_kwargs: {
            temperature: parseFloat(temperature),
            max_tokens: parseInt(maxToken),
          },
        },
      },
    };

    console.info('send message:', message);
    sendMessage(JSON.stringify(message));
    setMessages((prev) => {
      return [
        ...prev,
        {
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
    let optionList: SelectProps.Option[] = [];
    if (scenario.value === 'common') {
      optionList = LLM_BOT_COMMON_MODEL_LIST.map((item) => {
        return {
          label: item,
          value: item,
        };
      });
      setModelList(optionList);
      setModelOption(optionList?.[0]?.value ?? '');
    } else if (scenario.value === 'retail') {
      optionList = LLM_BOT_RETAIL_MODEL_LIST.map((item) => {
        return {
          label: item,
          value: item,
        };
      });
      setModelList(optionList);
      setModelOption(optionList?.[0]?.value ?? '');
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

  return (
    <CommonLayout
      isLoading={loadingHistory}
      activeHref={!historySessionId ? '/' : '/sessions'}
    >
      <div className="chat-container mt-10">
        <div className="chat-message flex-v flex-1 gap-10">
          {messages.map((msg, index) => (
            <Message
              showTrace={showTrace}
              key={identity(index)}
              type={msg.type}
              message={msg.message}
            />
          ))}
          {aiSpeaking && (
            <Message
              aiSpeaking={aiSpeaking}
              type="ai"
              showTrace={showTrace}
              message={{
                data: currentAIMessage,
                monitoring: currentMonitorMessage,
              }}
            />
          )}
        </div>

        <div className="flex-v gap-10">
          <div className="flex gap-5 send-message">
            <Select
              options={LLM_BOT_CHAT_MODE_LIST}
              selectedOption={chatModeOption}
              onChange={({ detail }) => {
                setChatModeOption(detail.selectedOption);
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
                  if (e.detail.key === 'Enter') {
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
                  onChange={({ detail }) => setUseChatHistory(detail.checked)}
                  checked={useChatHistory}
                >
                  {t('multiRound')}
                </Toggle>
                <Toggle
                  onChange={({ detail }) => setEnableTrace(detail.checked)}
                  checked={enableTrace}
                >
                  Enable trace
                </Toggle>
                {enableTrace && (
                  <Toggle
                    onChange={({ detail }) => setShowTrace(detail.checked)}
                    checked={showTrace}
                  >
                    Show trace
                  </Toggle>
                )}

                {/*
                <Toggle
                  onChange={({ detail }) => {
                    setGoogleAPIKeyError(false);
                    setUseWebSearch(detail.checked);
                  }}
                  checked={useWebSearch}
                >
                  Enable WebSearch
                </Toggle>
                {useWebSearch && (
                  <div style={{ minWidth: 300 }}>
                    <Input
                      invalid={googleAPIKeyError}
                      placeholder="Please input your Google API key"
                      value={googleAPIKey}
                      onChange={({ detail }) => {
                        setGoogleAPIKeyError(false);
                        setGoogleAPIKey(detail.value);
                      }}
                    />
                  </div>
                )}
                */}
              </div>
              <div className="flex align-center gap-10">
                <Box variant="p">{t('server')}: </Box>
                <StatusIndicator type={connectionStatus as any}>
                  {t(connectionStatus)}
                </StatusIndicator>
              </div>
            </div>
          </div>
          <div>
            <ExpandableSection
              onChange={({ detail }) => {
                setModelSettingExpand(detail.expanded);
              }}
              expanded={modelSettingExpand}
              // variant="footer"
              headingTagOverride="h4"
              headerText={t('modelSettings')}
            >
              <ColumnLayout columns={3} variant="text-grid">
                <FormField label={t('scenario')} stretch={true}>
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
                <SpaceBetween size="xs">
                  <FormField
                    label={t('modelName')}
                    stretch={true}
                    errorText={t(modelError)}
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
                  {showEndpoint && (
                    <FormField
                      label={t('endPoint')}
                      stretch={true}
                      errorText={t(endPointError)}
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
                  )}
                </SpaceBetween>
                <FormField
                  label={t('maxTokens')}
                  stretch={true}
                  errorText={t(maxTokenError)}
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
                  label={t('temperature')}
                  stretch={true}
                  errorText={t(temperatureError)}
                >
                  <Input
                    type="number"
                    value={temperature}
                    onChange={({ detail }) => {
                      setTemperatureError('');
                      setTemperature(detail.value);
                    }}
                  />
                </FormField>
              </ColumnLayout>
            </ExpandableSection>
          </div>
        </div>
      </div>
    </CommonLayout>
  );
};

export default ChatBot;
