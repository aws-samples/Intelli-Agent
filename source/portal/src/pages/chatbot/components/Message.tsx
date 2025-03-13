import {
  Button,
  ExpandableSection,
  Icon,
  Popover,
} from '@cloudscape-design/components';
import React, { useState } from 'react';
import Avatar from 'react-avatar';
import ReactMarkdown from 'react-markdown';
import { BounceLoader } from 'react-spinners';
import remarkGfm from 'remark-gfm';
import remarkHtml from 'remark-html';
import BedrockImg from 'src/assets/bedrock.webp';
import './Message.css';
import { DocumentData } from 'src/types';
import type { IconProps } from '@cloudscape-design/components';
import { useAppDispatch } from 'src/app/hooks';
import {
  setActiveDocumentId,
  // setAutoSendMessage,
} from 'src/app/slice/cs-workspace';

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

const Message: React.FC<MessageProps> = ({
  showTrace,
  type,
  message,
  aiSpeaking,
  documentList,
}) => {
  const dispatch = useAppDispatch();
  const handleDocClick = (source: string) => {
    dispatch(setActiveDocumentId(source));
  };

  const [showCopyTooltip, setShowCopyTooltip] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.data).then(() => {
      setShowCopyTooltip(true);
      setTimeout(() => setShowCopyTooltip(false), 2000); // 2秒后隐藏提示
    });
  };

  return (
    <>
      {type === 'ai' && (
        <>
          <div className="flex gap-10">
            {<Avatar size="40" round={true} src={BedrockImg} />}
            <div
              className={`message-content flex-1 ai`}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
            >
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
                        onClick={() => handleDocClick(doc.uuid)}
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
                    defaultExpanded={true}
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
              {isHovered && (
                <div
                  className="message-actions"
                  style={{
                    position: 'absolute',
                    bottom: '0px',
                    right: '0px',
                    backgroundColor: 'rgba(242, 243, 243, 0.8)',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    zIndex: 1,
                  }}
                >
                  <div
                    className="feedback-buttons"
                    style={{
                      display: 'flex',
                      justifyContent: 'flex-end',
                      gap: '8px',
                    }}
                  >
                    <Popover
                      dismissButton={false}
                      position="top"
                      size="small"
                      triggerType="custom"
                      content={showCopyTooltip ? 'Copied!' : ''}
                    >
                      <Button
                        iconName="copy"
                        variant="icon"
                        onClick={handleCopy}
                        ariaLabel="copy"
                      />
                    </Popover>
                    {/* <Button
                      iconName="send"
                      variant="icon"
                      onClick={() => {
                        console.log('send');
                        dispatch(setAutoSendMessage(message.data));
                      }}
                      ariaLabel="send"
                    /> */}
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
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
