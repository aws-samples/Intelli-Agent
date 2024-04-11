import React from 'react';
import Avatar from 'react-avatar';

interface MessageProps {
  type: 'ai' | 'human';
  message: string;
}

const Message: React.FC<MessageProps> = ({ type, message }) => {
  return (
    <div className="flex gap-10">
      {type === 'ai' && <Avatar size="40" round={true} name="A I" />}
      {type === 'human' && <Avatar size="40" round={true} name="User Name" />}
      <div className="message-content">{message}</div>
    </div>
  );
};

export default Message;
