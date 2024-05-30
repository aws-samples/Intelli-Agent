import { ExpandableSection } from '@cloudscape-design/components';
import React from 'react';
import Avatar from 'react-avatar';
import BedrockImg from 'src/assets/bedrock.webp';

interface MessageProps {
  type: 'ai' | 'human';
  message: {
    data: string;
    monitoring: string;
  };
}

const Message: React.FC<MessageProps> = ({ type, message }) => {
  return (
    <>
      {type === 'ai' && (
        <div className="flex gap-10">
          {<Avatar size="40" round={true} src={BedrockImg} />}
          <div className={`message-content flex-1 ai`}>
            <div className="message">{message.data}</div>
            {message.monitoring && (
              <div className="monitor mt-10">
                <ExpandableSection
                  variant="footer"
                  headingTagOverride="h5"
                  headerText="Monitoring"
                >
                  {message.monitoring}
                </ExpandableSection>
              </div>
            )}
          </div>
        </div>
      )}
      {type === 'human' && (
        <div className="flex align-end gap-10">
          <div className={`message-content human`}>
            <div className="message">{message.data}</div>
          </div>
        </div>
      )}
    </>
  );
};

export default Message;
