import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAppDispatch } from 'src/app/hooks';
import { setCurrentSessionId } from 'src/app/slice/cs-workspace';

interface UserChatListProps {
  leftTopHeight: number;
}

const UserChatList: React.FC<UserChatListProps> = ({ leftTopHeight }) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  //   const [currentChatId, setCurrentChatId] = useState('');
  const { id } = useParams();
  return (
    <div className="chat-list" style={{ height: leftTopHeight }}>
      <div className="section-header">
        <h3>Recent Chats</h3>
        <span className="counter">3 new</span>
      </div>
      <div className="chat-items">
        {[
          {
            id: '04f81649-79c7-41b5-96f5-863625c1ae26',
            name: 'haiyunc@amazon.com',
            message: 'I need help with my order #12345',
            time: '2min ago',
            isNew: false,
          },
          {
            id: '384fe22f-5f44-4b89-bd99-e651275ea79d',
            name: 'lvning@amazon.com',
            message: 'When will my refund be processed?',
            time: '15min ago',
            isNew: true,
          },
        ].map((chat) => (
          <div
            onClick={() => {
              //   setCurrentChatId(chat.id);
              dispatch(setCurrentSessionId(chat.id));
              navigate(`/custom-service/chat/${chat.id}`);
            }}
            key={chat.id}
            className={`chat-item ${id === chat.id ? 'active' : ''}`}
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
