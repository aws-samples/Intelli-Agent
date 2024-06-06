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
  LLM_BOT_MODEL_LIST,
  SCENARIO_LIST,
  RETAIL_GOODS_LIST,
} from 'src/utils/const';
import { v4 as uuidv4 } from 'uuid';
import { MessageDataType } from 'src/types';

interface MessageType {
  type: 'ai' | 'human';
  message: {
    data: string;
    monitoring: string;
  };
}

const ChatBot: React.FC = () => {
  const config = useContext(ConfigContext);
  const { t } = useTranslation();
  const auth = useAuth();

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
  const [modelOption, setModelOption] = useState<string>(LLM_BOT_MODEL_LIST[0]);
  const [chatModeOption, setChatModeOption] = useState<SelectProps.Option>(
    LLM_BOT_CHAT_MODE_LIST[0],
  );
  const [useChatHistory, setUseChatHistory] = useState(true);
  const [showTrace, setShowTrace] = useState(true);
  // const [useWebSearch, setUseWebSearch] = useState(false);
  // const [googleAPIKey, setGoogleAPIKey] = useState('');
  const [retailGoods, setRetailGoods] = useState<SelectProps.Option>(
    RETAIL_GOODS_LIST[0],
  );
  const [scenario, setScenario] = useState<SelectProps.Option>(
    SCENARIO_LIST[0],
  );

  const [sessionId, setSessionId] = useState('');
  const [workspaceIds, setWorkspaceIds] = useState<any[]>([]);

  const [temperature, setTemperature] = useState<number>(0.1);
  const [maxToken, setMaxToken] = useState(4096);

  const [showMessageError, setShowMessageError] = useState(false);
  // const [googleAPIKeyError, setGoogleAPIKeyError] = useState(false);

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

  useEffect(() => {
    setSessionId(uuidv4());
    getWorkspaceList();
  }, []);

  useEffect(() => {
    if (lastMessage !== null) {
      setAiSpeaking(true);
      console.info(lastMessage);
      const message: MessageDataType = JSON.parse(lastMessage.data);
      console.info('message:', message);
      if (message.message_type === 'MONITOR') {
        setCurrentMonitorMessage((prev) => {
          return prev + (message?.message ?? '');
        });
      } else {
        const isEnd = message.message_type === 'END';
        setCurrentAIMessage((prev) => {
          return prev + (message?.message?.content ?? '');
        });
        if (isEnd) {
          setAiSpeaking(false);
          setCurrentAIMessage('');
          setCurrentMonitorMessage('');
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
      }
    }
  }, [lastMessage]);

  const handleClickSendMessage = () => {
    if (aiSpeaking) {
      return;
    }
    if (!userMessage.trim()) {
      setShowMessageError(true);
      return;
    }
    setAiSpeaking(true);
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
        use_websearch: true,
        google_api_key: '',
        default_workspace_config: {
          intent_workspace_ids: [],
          rag_workspace_ids: workspaceIds,
        },
        default_llm_config: {
          model_id: modelOption,
          model_kwargs: { temperature: temperature, max_tokens: maxToken },
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

  return (
    <CommonLayout activeHref="/">
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
                disabled={aiSpeaking}
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
                  Multi-rounds
                </Toggle>
                <Toggle
                  onChange={({ detail }) => setShowTrace(detail.checked)}
                  checked={showTrace}
                >
                  Trace
                </Toggle>
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
              // variant="footer"
              headingTagOverride="h4"
              headerText="Model Settings"
            >
              <ColumnLayout columns={3} variant="text-grid">
                <FormField label="Model name" stretch={true}>
                  <Autosuggest
                    onChange={({ detail }) => setModelOption(detail.value)}
                    value={modelOption}
                    options={LLM_BOT_MODEL_LIST.map((item) => {
                      return {
                        label: item,
                        value: item,
                      };
                    })}
                    placeholder="Enter value"
                    empty="No matches found"
                  />
                </FormField>
                <FormField label="Scenario" stretch={true}>
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
                <FormField label="Max Tokens" stretch={true}>
                  <Input
                    value={maxToken.toString()}
                    onChange={({ detail }) => {
                      setMaxToken(parseFloat(detail.value));
                    }}
                  />
                </FormField>
                <FormField label="Temperature" stretch={true}>
                  <Input
                    value={temperature.toString()}
                    onChange={({ detail }) => {
                      setTemperature(parseFloat(detail.value));
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
