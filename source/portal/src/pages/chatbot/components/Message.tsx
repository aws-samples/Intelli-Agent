import React from 'react';
import Avatar from 'react-avatar';
import BedrockImg from 'src/assets/bedrock.webp';
import { useTranslation } from 'react-i18next';

interface MessageProps {
  type: 'ai' | 'human';
  message: string;
}

const Message: React.FC<MessageProps> = ({ type, message }) => {
  const { t } = useTranslation();
  return (
    <div className="flex gap-10">
      {type === 'ai' && <Avatar size="40" round={true} src={BedrockImg} />}
      {type === 'human' && <Avatar size="40" round={true} name={t('you')} />}
      <div className="message-content flex-1">{message}</div>
    </div>
  );
};

export default Message;
