import React, { useContext, useEffect, useState } from 'react';
import { useAuth } from 'react-oidc-context';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { useAppSelector } from 'src/app/hooks';
import ConfigContext from 'src/context/config-context';
import useAxiosWorkspaceRequest from 'src/hooks/useAxiosWorkspaceRequest';
import { ChatMessageResponse, ChatMessageType } from 'src/types';
import { formatTime } from 'src/utils/utils';
import { v4 as uuidv4 } from 'uuid';
const UserMessage: React.FC = () => {
  const config = useContext(ConfigContext);
  const csWorkspaceState = useAppSelector((state) => state.csWorkspace);
  const auth = useAuth();
  const request = useAxiosWorkspaceRequest();
  const [message, setMessage] = useState('');
  const [messageList, setMessageList] = useState<ChatMessageType[]>([]);
  const { lastMessage, sendMessage, readyState } = useWebSocket(
    `${config?.workspaceWebsocket}?idToken=${auth.user?.id_token}&user_id=${auth.user?.profile?.sub}&session_id=${csWorkspaceState.currentSessionId}&role=agent`,
    {
      onOpen: () => console.log('opened'),
      shouldReconnect: () => true,
    },
  );

  const getMessageList = async () => {
    const response: ChatMessageResponse = await request({
      url: `/customer-sessions/${csWorkspaceState.currentSessionId}/messages`,
      method: 'get',
    });
    console.info('response:', response);
    setMessageList(response.Items);
  };

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
        messageId: uuidv4(),
        role: 'agent',
        content: message,
        createTimestamp: new Date().toISOString(),
        additional_kwargs: {},
      },
    ]);
  };

  useEffect(() => {
    if (lastMessage) {
      console.log(lastMessage);
    }
  }, [lastMessage]);

  useEffect(() => {
    if (csWorkspaceState.currentSessionId) {
      getMessageList();
      // 设置1秒轮询
      const interval = setInterval(getMessageList, 2000);
      // 清理函数
      return () => clearInterval(interval);
    }
  }, [csWorkspaceState.currentSessionId]);

  return (
    <div className="user-message-container">
      <div className="messages">
        {messageList.map((message) => (
          <div key={message.messageId} className={`message ${message.role}`}>
            <div className="message-content">
              <p>{message.content}</p>
              <span className="time">
                {formatTime(message.createTimestamp)}
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="input-area">
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
          <span className="icon">💬</span>
          Send
        </button>
      </div>
    </div>
  );
};

export default UserMessage;
