import React, { useState, useEffect, useCallback } from 'react';
import mammoth from 'mammoth';

interface WordPreviewProps {
  source: string;
}

const extractFilePath = (s3Url: string) => {
  const regex = /s3:\/\/[^\/]+(\/.*)/;
  const match = s3Url.match(regex);
  if (match && match[1]) {
    const originalPath = match[1];
    const encodedPath = originalPath
      .split('/')
      .map((segment) => encodeURIComponent(segment))
      .join('/');
    return encodedPath;
  }
  return '';
};

const convertMarkdownImages = (content: string): string => {
  content = content.replace(
    /!\[image\]\(([^)]+)\)/g,
    '<img src="$1" alt="image" style="max-width: 100%; height: auto;" />',
  );

  content = content.replace(
    /!\[([^\]]*)\]\(([^)"]+)(?:\s+"([^"]*)")?\)/g,
    '<img src="$2" alt="$1" title="$3" style="max-width: 100%; height: auto;" />',
  );

  return content;
};

const DocFileViewer: React.FC<WordPreviewProps> = ({ source }) => {
  const [docContent, setDocContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [fileUrl, setFileUrl] = useState<string>('');
  const [fileType, setFileType] = useState<'pdf' | 'docx' | null>(null);

  const determineFileType = (url: string): 'pdf' | 'docx' | null => {
    if (url.toLowerCase().endsWith('.pdf')) {
      return 'pdf';
    } else if (url.toLowerCase().endsWith('.docx')) {
      return 'docx';
    }
    return null;
  };

  const fetchAndParseDocx = useCallback(async (docFileUrl: string) => {
    try {
      setIsLoading(true);
      setError('');

      const response = await fetch(docFileUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch document: ${response.statusText}`);
      }

      const arrayBuffer = await response.arrayBuffer();
      const result = await mammoth.convertToHtml({ arrayBuffer });
      const processedContent = convertMarkdownImages(result.value);
      setDocContent(processedContent);
      setError('');
    } catch (error) {
      console.error('Error fetching or parsing the document:', error);
      setError('Failed to load document. Please try again later.');
      setDocContent('');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleDownload = () => {
    window.open(fileUrl, '_blank');
  };

  useEffect(() => {
    if (source) {
      setIsLoading(true);
      setError('');
      setDocContent('');

      const filePath = extractFilePath(source);
      const url = 'https://d36nadexhza1cw.cloudfront.net' + filePath;
      setFileUrl(url);

      const type = determineFileType(url);
      setFileType(type);

      if (type === 'docx') {
        fetchAndParseDocx(url);
      } else if (type === 'pdf') {
        setIsLoading(false);
      } else {
        setError('Unsupported file type');
        setIsLoading(false);
      }
    }
  }, [source, fetchAndParseDocx]);

  return (
    <div
      className="doc-viewer-container"
      style={{
        minHeight: '500px',
        width: '100%',
        backgroundColor: '#fff',
        border: '1px solid #e8e8e8',
        borderRadius: '4px',
        padding: '20px',
        overflow: 'auto',
      }}
    >
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          Loading document...
        </div>
      ) : error ? (
        <div
          style={{
            textAlign: 'center',
            padding: '20px',
            color: '#ff4d4f',
          }}
        >
          {error}
        </div>
      ) : fileType === 'pdf' ? (
        <div>
          <div style={{ marginBottom: '20px', textAlign: 'right' }}>
            <button
              onClick={handleDownload}
              style={{
                padding: '8px 16px',
                backgroundColor: '#1890ff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Download PDF
            </button>
          </div>
          <iframe
            src={`https://docs.google.com/viewer?url=${encodeURIComponent(
              fileUrl,
            )}&embedded=true`}
            style={{
              width: '100%',
              height: '800px',
              border: 'none',
            }}
            title="PDF Viewer"
          />
        </div>
      ) : docContent ? (
        <div
          className="document-content"
          style={{
            padding: '20px',
            lineHeight: '1.6',
          }}
          dangerouslySetInnerHTML={{ __html: docContent }}
        />
      ) : (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          No content available
        </div>
      )}
    </div>
  );
};

export default DocFileViewer;
