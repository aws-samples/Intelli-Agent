import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch } from 'src/app/hooks';
import { setCurrentSessionId } from 'src/app/slice/cs-workspace';

interface UserChatListProps {
  leftTopHeight: number;
}

const UserChatList: React.FC<UserChatListProps> = ({ leftTopHeight }) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  return (
    <div className="chat-list" style={{ height: leftTopHeight }}>
      <div className="section-header">
        <h3>Recent Chats</h3>
        <span className="counter">3 new</span>
      </div>
      <div className="chat-items">
        {[
          {
            id: '4c290970-2245-47a3-9404-ccd228cd3374',
            name: 'Sarah Wilson',
            message: 'I need help with my order #12345',
            time: '2min ago',
            isNew: true,
          },
          {
            id: '6726d90c-bbdb-47cd-99fb-392129a219a2',
            name: 'Mike Johnson',
            message: 'When will my refund be processed?',
            time: '15min ago',
            isNew: true,
          },
          {
            id: '10745e4d-d9f6-496b-a45e-a01a41147f5d',
            name: 'Emma Davis',
            message: 'Thanks for your help!',
            time: '1h ago',
            isNew: false,
          },
        ].map((chat) => (
          <div
            onClick={() => {
              dispatch(setCurrentSessionId(chat.id));
              navigate(`/custom-service/chat/${chat.id}`);
            }}
            key={chat.id}
            className={`chat-item ${chat.isNew ? 'new' : ''}`}
          >
            <div className="user-avatar">{chat.name.charAt(0)}</div>
            <div className="chat-info">
              <div className="chat-header">
                <span className="name">{chat.name}</span>
                <span className="time">{chat.time}</span>
              </div>
              <p className="last-message">{chat.message}</p>
            </div>
            {chat.isNew && <div className="new-badge" />}
          </div>
        ))}
      </div>
    </div>
  );
};

export default UserChatList;
