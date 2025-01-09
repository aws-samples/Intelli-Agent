import React, { useContext, useEffect, useState } from 'react';
import { useAuth } from 'react-oidc-context';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { useAppSelector } from 'src/app/hooks';
import ConfigContext from 'src/context/config-context';

const UserMessage: React.FC = () => {
  const config = useContext(ConfigContext);
  const csWorkspaceState = useAppSelector((state) => state.csWorkspace);
  const auth = useAuth();
  const [message, setMessage] = useState('');
  const [messageList, setMessageList] = useState<
    {
      id: number;
      type: string;
      text: string;
      time: string;
    }[]
  >([
    {
      id: 1,
      type: 'customer',
      text: 'Hello, I am a customer service agent. How can I assist you today?',
      time: '14:30',
    },
  ]);
  const { lastMessage, sendMessage, readyState } = useWebSocket(
    `${config?.workspaceWebsocket}?idToken=${auth.user?.id_token}&user_id=${auth.user?.profile?.sub}&session_id=${csWorkspaceState.currentSessionId}&role=agent`,
    {
      onOpen: () => console.log('opened'),
      shouldReconnect: () => true,
    },
  );

  const handleSend = () => {
    if (!message.trim()) return;

    const sendMessageObj = {
      query: message,
      entry_type: 'common',
      session_id: csWorkspaceState.currentSessionId,
      user_id: auth.user?.profile?.sub,
      action: 'sendResponse',
    };
    sendMessage(JSON.stringify(sendMessageObj));

    setMessage('');
    setMessageList((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        type: 'agent',
        text: message,
        time: new Date().toLocaleTimeString(),
      },
    ]);
    // setMessageList((prev) => [...prev, sendMessageObj]);
  };

  useEffect(() => {
    if (lastMessage) {
      console.log(lastMessage);
    }
  }, [lastMessage]);

  return (
    <>
      <div className="messages">
        {messageList.map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-content">
              <p>{message.text}</p>
              <span className="time">{message.time}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="chat-input">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message..."
          rows={3}
        />
        <button
          onClick={() => {
            handleSend();
          }}
          className="send-btn"
          disabled={readyState !== ReadyState.OPEN}
        >
          <span className="icon">📤</span>
          Send
        </button>
      </div>
    </>
  );
};

export default UserMessage;
