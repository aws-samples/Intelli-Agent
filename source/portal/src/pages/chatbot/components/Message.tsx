import { ExpandableSection, Icon } from '@cloudscape-design/components';
import React from 'react';
import Avatar from 'react-avatar';
import ReactMarkdown from 'react-markdown';
import { BounceLoader } from 'react-spinners';
import remarkGfm from 'remark-gfm';
import remarkHtml from 'remark-html';
import BedrockImg from 'src/assets/bedrock.webp';
import './Message.css';
import { DocumentData } from 'src/types';
import type { IconProps } from '@cloudscape-design/components';

interface MessageProps {
  type: 'ai' | 'human';
  message: {
    data: string;
    monitoring: string;
  };
  showTrace?: boolean;
  aiSpeaking?: boolean;
  documentList?: DocumentData[];
}

const getFileIcon = (fileName: string): IconProps['name'] => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  switch (extension) {
    case 'pdf':
      return 'file-open';
    case 'doc':
    case 'docx':
      return 'file-open';
    case 'xls':
    case 'xlsx':
      return 'file-open';
    case 'ppt':
    case 'pptx':
      return 'file-open';
    default:
      return 'file-open';
  }
};

const handleDocClick = (source: string) => {
  window.open(source, '_blank');
};

const Message: React.FC<MessageProps> = ({
  showTrace,
  type,
  message,
  aiSpeaking,
  documentList,
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
            {documentList && documentList.length > 0 && (
              <div className="document-list">
                {documentList.map((doc) => {
                  const fileName = doc.source.split('/').pop() || '';
                  const iconName = getFileIcon(fileName);

                  return (
                    <div
                      key={doc.page_content}
                      className="document-item"
                      onClick={() => handleDocClick(doc.source)}
                    >
                      <Icon name={iconName} />
                      <span className="doc-name" title={fileName}>
                        {fileName}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
            {showTrace && message.monitoring && (
              <div className="monitor mt-10">
                <ExpandableSection
                  variant="footer"
                  headingTagOverride="h5"
                  headerText="Monitoring"
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkHtml]}
                    components={{
                      h1: ({ node, ...props }) => (
                        <h1 className="custom-header" {...props} />
                      ),
                      h2: ({ node, ...props }) => (
                        <h2 className="custom-header" {...props} />
                      ),
                      h3: ({ node, ...props }) => (
                        <h3 className="custom-header" {...props} />
                      ),
                      table: ({ node, ...props }) => (
                        <table className="custom-table" {...props} />
                      ),
                      th: ({ node, ...props }) => (
                        <th className="custom-table-header" {...props} />
                      ),
                      td: ({ node, ...props }) => (
                        <td className="custom-table-cell" {...props} />
                      ),
                      img: ({ node, ...props }) => (
                        <img
                          {...props}
                          className="markdown-table-image"
                          style={{ maxWidth: '150px', height: 'auto' }}
                        />
                      ),
                    }}
                  >
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
