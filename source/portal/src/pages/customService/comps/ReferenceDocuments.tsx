import React, { useState } from 'react';
interface Document {
  id: string;
  title: string;
  content: string;
  lastModified: string;
  type: string;
}

const ReferenceDocuments: React.FC = () => {
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [documents] = useState<Document[]>([
    {
      id: 'doc1',
      title: 'Refund Policy',
      content: `# Refund Policy
      
Our refund policy is designed to ensure customer satisfaction while protecting our business interests. Here are the key points:

1. Full refunds are available within 30 days of purchase
2. Items must be unused and in original packaging
3. Shipping costs are non-refundable
4. Digital products have a 14-day refund window

## Process
1. Submit a refund request through your account
2. Receive a return authorization
3. Ship the item back to our returns center
4. Refund will be processed within 5-7 business days

For more information, contact customer service.`,
      lastModified: '2024-03-15',
      type: 'Policy',
    },
    {
      id: 'doc2',
      title: 'Shipping Guidelines',
      content: `# Shipping Guidelines

Standard shipping times and costs:

- Domestic (2-5 business days): $5.99
- International (7-14 business days): $19.99
- Express (1-2 business days): $14.99

## Tracking
All orders include tracking information sent via email.

## Restrictions
Some items cannot be shipped to certain locations due to regulations.`,
      lastModified: '2024-03-14',
      type: 'Guide',
    },
    {
      id: 'doc3',
      title: 'Customer Support FAQ',
      content: `# Frequently Asked Questions

## Account Issues
1. How do I reset my password?
2. Where can I find my order history?
3. How do I update my payment method?

## Orders
1. Can I modify my order?
2. What's your cancellation policy?
3. How do I track my package?

## Returns
1. How do I start a return?
2. What's your return policy?
3. How long do refunds take?`,
      lastModified: '2024-03-13',
      type: 'Support',
    },
  ]);
  return (
    <div className="docs-tabs">
      <div className="tabs-list">
        {documents.map((doc) => (
          <button
            key={doc.id}
            className={`tab ${activeDocId === doc.id ? 'active' : ''}`}
            onClick={() => setActiveDocId(doc.id)}
          >
            <span className="title">{doc.title}</span>
            <span className="badge">{doc.type}</span>
          </button>
        ))}
      </div>
      <div className="tab-content">
        {activeDocId ? (
          <div className="document-preview">
            <div className="doc-header">
              <h2>{documents.find((d) => d.id === activeDocId)?.title}</h2>
              <span className="last-modified">
                Last modified:{' '}
                {documents.find((d) => d.id === activeDocId)?.lastModified}
              </span>
            </div>
            <div className="doc-content markdown">
              {documents.find((d) => d.id === activeDocId)?.content}
            </div>
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
