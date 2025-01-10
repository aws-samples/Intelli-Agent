import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAppDispatch } from 'src/app/hooks';
import {
  setCurrentSessionId,
  setCurrentUser,
} from 'src/app/slice/cs-workspace';
import useAxiosWorkspaceRequest from 'src/hooks/useAxiosWorkspaceRequest';
import { ChatSessionResponse, ChatSessionType } from 'src/types';
import { formatTime } from 'src/utils/utils';

interface UserChatListProps {
  leftTopHeight: number;
}

interface ExtendedChatSessionType extends ChatSessionType {
  isNew?: boolean;
}

const UserChatList: React.FC<UserChatListProps> = ({ leftTopHeight }) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  //   const [currentChatId, setCurrentChatId] = useState('');
  const request = useAxiosWorkspaceRequest();
  const [chatList, setChatList] = useState<ExtendedChatSessionType[]>([]);
  const [prevChatList, setPrevChatList] = useState<ExtendedChatSessionType[]>(
    [],
  );

  const getChatList = async () => {
    const response: ChatSessionResponse = await request({
      url: '/customer-sessions',
      params: {
        max_items: 9999,
        page_size: 9999,
      },
      method: 'get',
    });

    const newChatList = response.Items.map((chat) => {
      const prevChat = prevChatList.find(
        (prev) => prev.sessionId === chat.sessionId,
      );
      const isNew = prevChat
        ? chat.latestQuestion !== prevChat.latestQuestion
        : true;
      return {
        ...chat,
        isNew: isNew && chat.sessionId !== id,
      };
    });

    setPrevChatList(chatList);
    setChatList(newChatList);
  };

  const selectChatSession = async (sessionId: string) => {
    setChatList((prev) =>
      prev.map((chat) => ({
        ...chat,
        isNew: chat.sessionId === sessionId ? false : chat.isNew,
      })),
    );

    const response = await request({
      url: '/customer-sessions',
      method: 'post',
      data: {
        session_id: sessionId,
      },
    });
    console.info('response:', response);
    getChatList();
  };

  useEffect(() => {
    getChatList();
    const interval = setInterval(getChatList, 2000);

    return () => clearInterval(interval);
  }, []);

  const { id } = useParams();
  return (
    <div className="chat-list" style={{ height: leftTopHeight }}>
      <div className="section-header">
        <h3>Recent Chats</h3>
        <span className="counter">
          {chatList.filter((chat) => chat.isNew).length} new
        </span>
      </div>
      <div className="chat-items">
        {chatList.map((chat) => (
          <div
            onClick={() => {
              dispatch(setCurrentUser(chat));
              selectChatSession(chat.sessionId);
              dispatch(setCurrentSessionId(chat.sessionId));
              navigate(`/custom-service/chat/${chat.sessionId}`);
            }}
            key={chat.sessionId}
            className={`chat-item ${id === chat.sessionId ? 'active' : ''}`}
          >
            <div className="user-avatar">{chat.userId.charAt(0)}</div>
            <div className="chat-info">
              <div className="chat-header">
                <span className="name">{chat.userId}</span>
                <span className="time">
                  {formatTime(chat.lastModifiedTimestamp)}
                </span>
              </div>
              <p className="last-message">{chat.latestQuestion}</p>
            </div>
            {chat.isNew && <div className="new-badge" />}
          </div>
        ))}
      </div>
    </div>
  );
};

export default UserChatList;
