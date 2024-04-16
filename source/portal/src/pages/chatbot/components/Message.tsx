import React from 'react';
import Avatar from 'react-avatar';
import BedrockImg from '../../../assets/bedrock.webp';

interface MessageProps {
  type: 'ai' | 'human';
  message: string;
}

const Message: React.FC<MessageProps> = ({ type, message }) => {
  return (
    <div className="flex gap-10">
      {type === 'ai' && <Avatar size="40" round={true} src={BedrockImg} />}
      {type === 'human' && <Avatar size="40" round={true} name="You" />}
      <div className="message-content flex-1">{message}</div>
    </div>
  );
};

export default Message;
