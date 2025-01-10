import React from 'react';
import DocViewer, { DocViewerRenderers } from 'react-doc-viewer';

const extractFilePath = (s3Url: string) => {
  // 用正则表达式从 S3 URL 中提取出路径部分
  const regex = /s3:\/\/[^\/]+(\/.*)/;
  const match = s3Url.match(regex);

  if (match && match[1]) {
    return match[1];
  }
  return '';
};

interface DocViewerProps {
  source: string;
}

const DocFileViewer: React.FC<DocViewerProps> = ({ source }) => {
  const filePath = extractFilePath(source);

  return (
    <div className="doc-viewer-container">
      <DocViewer
        documents={[
          {
            uri: 'https://d36nadexhza1cw.cloudfront.net' + filePath,
          },
        ]}
        pluginRenderers={DocViewerRenderers}
        style={{ height: '100%' }}
        config={{
          header: {
            disableHeader: true,
            disableFileName: true,
          },
        }}
      />
    </div>
  );
};

export default DocFileViewer;
