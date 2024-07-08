import { ExpandableSection } from '@cloudscape-design/components';
import React from 'react';
import Avatar from 'react-avatar';
import ReactMarkdown from 'react-markdown';
import { BounceLoader } from 'react-spinners';
import remarkGfm from 'remark-gfm';
import BedrockImg from 'src/assets/bedrock.webp';

interface MessageProps {
  type: 'ai' | 'human';
  message: {
    data: string;
    monitoring: string;
  };
  showTrace?: boolean;
  aiSpeaking?: boolean;
}

const Message: React.FC<MessageProps> = ({
  showTrace,
  type,
  message,
  aiSpeaking,
}) => {
  return (
    <>
      {type === 'ai' && (
        <div className="flex gap-10">
          {<Avatar size="40" round={true} src={BedrockImg} />}
          <div className={`message-content flex-1 ai`}>
            <div className="message">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.data.replace(/~/g, '\\~')}
              </ReactMarkdown>
              {aiSpeaking && (
                <div className="mt-5">
                  <BounceLoader size="12px" color="#888" />
                </div>
              )}
            </div>
            {showTrace && message.monitoring && (
              <div className="monitor mt-10">
                <ExpandableSection
                  variant="footer"
                  headingTagOverride="h5"
                  headerText="Monitoring"
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.monitoring}
                  </ReactMarkdown>
                </ExpandableSection>
              </div>
            )}
          </div>
        </div>
      )}
      {type === 'human' && (
        <div className="flex align-end gap-10">
          <div className={`message-content human`}>
            <div className="message">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.data}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Message;
