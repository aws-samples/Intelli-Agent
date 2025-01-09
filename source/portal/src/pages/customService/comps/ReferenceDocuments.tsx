import { Alert, SpaceBetween } from '@cloudscape-design/components';
import React, { useEffect, useState } from 'react';
import { useAppSelector } from 'src/app/hooks';

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
            <div className="doc-header">
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
            <SpaceBetween direction="horizontal" size="xl">
              <div className="doc-content markdown">
                <Alert type="info" header="Retrieval Content">
                  {
                    csWorkspaceState.documentList.find(
                      (d) => d.uuid === activeDocId,
                    )?.retrieval_content
                  }
                </Alert>
              </div>
              <div className="doc-content markdown">
                <Alert type="info" header="Page Content">
                  {
                    csWorkspaceState.documentList.find(
                      (d) => d.uuid === activeDocId,
                    )?.page_content
                  }
                </Alert>
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
