import React, { useContext, useEffect, useState, useRef } from 'react';
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isSending, setIsSending] = useState(false);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const messagesRef = useRef<HTMLDivElement>(null);

  const getMessageList = async () => {
    const response: ChatMessageResponse = await request({
      url: `/customer-sessions/${csWorkspaceState.currentSessionId}/messages`,
      method: 'get',
    });
    console.info('response:', response);
    setMessageList(response.Items);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 处理消息区域的滚动事件
  const handleScroll = () => {
    if (!messagesRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = messagesRef.current;
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 50;

    // 只有当用户滚动到接近底部时，才重新启用自动滚动
    setShouldAutoScroll(isAtBottom);
  };

  // 当消息列表更新时滚动到底部
  useEffect(() => {
    if (shouldAutoScroll) {
      scrollToBottom();
    }
  }, [messageList, shouldAutoScroll]);

  const handleSend = async () => {
    if (!message.trim()) return;

    setIsSending(true);
    const sendMessageObj = {
      query: message,
      entry_type: 'common',
      session_id: csWorkspaceState.currentSessionId,
      user_id: auth.user?.profile?.sub,
      action: 'sendResponse',
    };

    try {
      sendMessage(JSON.stringify(sendMessageObj));
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
      setMessage('');
      // 发送消息后重新启用自动滚动
      setShouldAutoScroll(true);
    } finally {
      setIsSending(false);
    }
  };

  useEffect(() => {
    if (lastMessage) {
      console.log(lastMessage);
    }
  }, [lastMessage]);

  useEffect(() => {
    if (csWorkspaceState.currentSessionId) {
      getMessageList();

      let intervalId: any = null;

      // 只在非发送状态时启动轮询
      if (!isSending) {
        intervalId = setInterval(getMessageList, 2000);
      }

      return () => {
        if (intervalId) {
          clearInterval(intervalId);
        }
      };
    }
  }, [csWorkspaceState.currentSessionId, isSending]); // 添加 isSending 作为依赖

  return (
    <div className="user-message-container">
      <div className="messages" ref={messagesRef} onScroll={handleScroll}>
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
        <div ref={messagesEndRef} />
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
