import {
  Alert,
  ExpandableSection,
  SpaceBetween,
} from '@cloudscape-design/components';
import React, { useEffect, useState } from 'react';
import { useAppSelector } from 'src/app/hooks';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkHtml from 'remark-html';

import DocFileViewer from './DocFileViewer';
const ReferenceDocuments: React.FC = () => {
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const csWorkspaceState = useAppSelector((state) => state.csWorkspace);

  useEffect(() => {
    if (csWorkspaceState.activeDocumentId) {
      setActiveDocId(csWorkspaceState.activeDocumentId);
    }
  }, [csWorkspaceState.activeDocumentId]);

  return (
    <div className="docs-tabs">
      <div className="tabs-list">
        {csWorkspaceState.documentList.map((doc) => (
          <button
            key={doc.uuid}
            className={`tab ${activeDocId === doc.uuid ? 'active' : ''}`}
            onClick={() => setActiveDocId(doc.uuid)}
          >
            <span className="title">{doc.source.split('/').pop()}</span>
            {activeDocId === doc.uuid && <span className="active-indicator" />}
          </button>
        ))}
      </div>
      <div className="tab-content">
        {activeDocId ? (
          <div className="document-preview">
            <SpaceBetween direction="vertical" size="s">
              <ExpandableSection headerText="Page Content">
                <Alert>
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkHtml]}>
                    {
                      csWorkspaceState.documentList.find(
                        (d) => d.uuid === activeDocId,
                      )?.page_content
                    }
                  </ReactMarkdown>
                </Alert>
              </ExpandableSection>
              <ExpandableSection headerText="Retrieval Content">
                <Alert>
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkHtml]}>
                    {
                      csWorkspaceState.documentList.find(
                        (d) => d.uuid === activeDocId,
                      )?.retrieval_content
                    }
                  </ReactMarkdown>
                </Alert>
              </ExpandableSection>
              <div>
                <div className="doc-header flex align-center justify-between">
                  <h2>
                    {csWorkspaceState.documentList
                      .find((d) => d.uuid === activeDocId)
                      ?.source.split('/')
                      .pop()}
                  </h2>
                  <span className="last-modified">
                    Retrieval Score:{' '}
                    {
                      csWorkspaceState.documentList.find(
                        (d) => d.uuid === activeDocId,
                      )?.retrieval_score
                    }
                  </span>
                </div>
                <DocFileViewer
                  key={activeDocId}
                  source={
                    csWorkspaceState.documentList.find(
                      (d) => d.uuid === activeDocId,
                    )?.source || ''
                  }
                />
              </div>
            </SpaceBetween>
          </div>
        ) : (
          <div className="no-doc-selected">
            <p>Select a document to preview its content</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReferenceDocuments;
