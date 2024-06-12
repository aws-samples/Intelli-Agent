import React from 'react';
import { useParams } from 'react-router-dom';
import ChatBot from '../chatbot/ChatBot';

const SessionDetail: React.FC = () => {
  const { id } = useParams();
  return (
    <div>
      <ChatBot historySessionId={id} />
    </div>
  );
};

export default SessionDetail;
