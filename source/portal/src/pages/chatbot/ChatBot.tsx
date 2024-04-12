import React, { useContext, useEffect, useState } from 'react';
import CommonLayout from '../../layout/CommonLayout';
import Message from './components/Message';
import {
  Box,
  Button,
  Modal,
  SpaceBetween,
  StatusIndicator,
  Textarea,
} from '@cloudscape-design/components';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { identity } from 'lodash';
import ConfigContext from '../../context/config-context';

interface MessageType {
  type: 'ai' | 'human';
  message: string;
}

const ChatBot: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const config = useContext(ConfigContext);

  const [messages, setMessages] = useState<MessageType[]>([
    {
      type: 'ai',
      message: 'Hello, how can I help you today?',
    },
  ]);
  const [userMessage, setUserMessage] = useState('');
  const { lastMessage, sendMessage, readyState } = useWebSocket(
    config?.websocket ?? '',
    {
      onOpen: () => console.log('opened'),
      //Will attempt to reconnect on all close events, such as server shutting down
      shouldReconnect: () => true,
    },
  );
  const [currentAIMessage, setCurrentAIMessage] = useState('');
  const [aiSpeaking, setAiSpeaking] = useState(false);

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'loading',
    [ReadyState.OPEN]: 'success',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'error',
    [ReadyState.UNINSTANTIATED]: 'pending',
  }[readyState];

  useEffect(() => {
    if (lastMessage !== null) {
      setAiSpeaking(true);
      console.info(lastMessage);
      const message = JSON.parse(lastMessage.data);
      console.info('message:', message);
      const chunkMessage = message.choices?.[0];
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
      temperature: 0.1,
      type: 'common',
      retriever_config: { workspace_ids: ['lvntest'] },
    };
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
                placeholder="Type a message"
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
                Send
              </Button>
            </div>
          </div>
          <div className="flex space-between">
            <div>
              <Button iconName="settings" onClick={() => setVisible(true)}>
                Model Settings
              </Button>
            </div>
            <div>
              Server:{' '}
              <StatusIndicator type={connectionStatus as any}>
                {connectionStatus}
              </StatusIndicator>
            </div>
          </div>
        </div>
      </div>
      <Modal
        onDismiss={() => setVisible(false)}
        visible={visible}
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                variant="link"
                onClick={() => {
                  setVisible(false);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  setVisible(false);
                }}
              >
                Confirm
              </Button>
            </SpaceBetween>
          </Box>
        }
        header="Modal title"
      >
        Settings are in here!
      </Modal>
    </CommonLayout>
  );
};

export default ChatBot;