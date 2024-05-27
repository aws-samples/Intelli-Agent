import React, { useContext, useEffect, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import Message from './components/Message';
import { useTranslation } from 'react-i18next';
import {
  Autosuggest,
  Box,
  Button,
  ColumnLayout,
  ExpandableSection,
  FormField,
  Input,
  StatusIndicator,
  Textarea,
  Toggle,
} from '@cloudscape-design/components';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { identity } from 'lodash';
import ConfigContext from 'src/context/config-context';
import { useAuth } from 'react-oidc-context';
import { LLM_BOT_MODEL_LIST } from 'src/utils/const';
import { v4 as uuidv4 } from 'uuid';

interface MessageType {
  type: 'ai' | 'human';
  message: string;
}

const ChatBot: React.FC = () => {
  const config = useContext(ConfigContext);
  const { t } = useTranslation();
  const auth = useAuth();

  const [messages, setMessages] = useState<MessageType[]>([
    {
      type: 'ai',
      message: t('welcomeMessage'),
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
  // const [currentMonitorMessage, setCurrentMonitorMessage] = useState('');
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [modelOption, setModelOption] = useState<string>(LLM_BOT_MODEL_LIST[0]);
  const [sessionId, setSessionId] = useState('');

  const [enableOption, setEnableOption] = useState(false);
  const [temperature, setTemperature] = useState<number>(0.1);
  const [maxToken, setMaxToken] = useState(4096);

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'loading',
    [ReadyState.OPEN]: 'success',
    [ReadyState.CLOSING]: 'closing',
    [ReadyState.CLOSED]: 'error',
    [ReadyState.UNINSTANTIATED]: 'pending',
  }[readyState];

  useEffect(() => {
    setSessionId(uuidv4());
  }, []);

  useEffect(() => {
    if (lastMessage !== null) {
      setAiSpeaking(true);
      console.info(lastMessage);
      const message = JSON.parse(lastMessage.data);
      console.info('message:', message);
      const chunkMessage = message.choices?.[0];
      // TODO handle multiple message types
      // message_type = 'END' | 'CHUNK' | 'MONITOR'
      if (chunkMessage) {
        const isEnd = chunkMessage.message_type === 'END';
        setCurrentAIMessage((prev) => {
          return prev + (chunkMessage?.message?.content ?? '');
        });
        if (isEnd) {
          setAiSpeaking(false);
          setCurrentAIMessage('');
          setMessages((prev) => {
            return [...prev, { type: 'ai', message: currentAIMessage }];
          });
        }
      }
    }
  }, [lastMessage]);

  const handleClickSendMessage = () => {
    const message = {
      action: 'sendMessage',
      messages: [{ role: 'user', content: userMessage }],
      temperature: temperature,
      type: 'common',
      retriever_config: {
        workspace_ids: auth.user?.profile?.['cognito:groups'] ?? [],
      },
      query: userMessage,
      entry_type: 'common',
      session_id: sessionId,
      chatbot_config: {
        intention_config: {
          retrievers: [
            {
              type: 'qq',
              workspace_ids: auth.user?.profile?.['cognito:groups'] ?? [],
              config: {
                top_k: 10,
              },
            },
          ],
        },
        query_process_config: {
          conversation_query_rewrite_config: {
            model_id: modelOption,
          },
        },
        agent_config: {
          model_id: modelOption,
          model_kwargs: { temperature: temperature, max_tokens: maxToken },
          tools: [{ name: 'give_final_response' }, { name: 'search_lihoyo' }],
        },
        chat_config: {
          model_id: modelOption,
        },
      },
    };
    console.info('send message:', message);
    sendMessage(JSON.stringify(message));
    setMessages((prev) => {
      return [...prev, { type: 'human', message: userMessage }];
    });
    setUserMessage('');
  };

  return (
    <CommonLayout activeHref="/">
      <div className="chat-container mt-10">
        <div className="chat-message flex-v flex-1 gap-10">
          {messages.map((msg, index) => (
            <Message
              key={identity(index)}
              type={msg.type}
              message={msg.message}
            />
          ))}
          {aiSpeaking && <Message type="ai" message={currentAIMessage} />}
        </div>

        <div className="flex-v gap-10">
          <div className="flex gap-10 send-message">
            <div className="flex-1 pr">
              <Textarea
                rows={1}
                value={userMessage}
                placeholder={t('typeMessage')}
                onChange={(e) => setUserMessage(e.detail.value)}
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
              <div className="flex gap-10">
                <Toggle
                  onChange={({ detail }) => setEnableOption(detail.checked)}
                  checked={enableOption}
                >
                  Stream
                </Toggle>
                <Toggle
                  onChange={({ detail }) => setEnableOption(detail.checked)}
                  checked={enableOption}
                >
                  Use Knowledge QA
                </Toggle>
                <Toggle
                  onChange={({ detail }) => setEnableOption(detail.checked)}
                  checked={enableOption}
                >
                  Multi-rounds
                </Toggle>
                <Toggle
                  onChange={({ detail }) => setEnableOption(detail.checked)}
                  checked={enableOption}
                >
                  Hide Ref Doc
                </Toggle>
                <Toggle
                  onChange={({ detail }) => setEnableOption(detail.checked)}
                  checked={enableOption}
                >
                  Trace
                </Toggle>
                <Toggle
                  onChange={({ detail }) => setEnableOption(detail.checked)}
                  checked={enableOption}
                >
                  Enable Websearch
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
                    ariaLabel="Autosuggest example with suggestions"
                    placeholder="Enter value"
                    empty="No matches found"
                  />
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
              <ColumnLayout columns={3} variant="text-grid">
                <FormField label="System Role Name" stretch={true}>
                  <Input value="" />
                </FormField>
                <FormField label="System Role Prompt" stretch={true}>
                  <Input value="" />
                </FormField>
                <FormField label="Prompt template" stretch={true}>
                  <Input value="" />
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
