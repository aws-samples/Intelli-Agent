import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { TopNavigation } from '@cloudscape-design/components';
import {
  DEFAULT_ZH_LANG,
  EN_TEXT,
  LANGUAGE_ITEMS,
  ZH_LANGUAGE_LIST,
  ZH_TEXT,
} from 'src/utils/const';
import './CustomerService.scss';
import { initResize } from './resize';
import { ChatMessage } from './comps/ChatMessage';
import { useAppSelector } from 'src/app/hooks';

const INIT_WIDTH = 400;
const MAX_WIDTH = 800;

interface Document {
  id: string;
  title: string;
  content: string;
  lastModified: string;
  type: string;
}

const CustomerService: React.FC = () => {
  const { t, i18n } = useTranslation();
  const displayName = 'Ning';
  const [leftWidth, setLeftWidth] = useState(INIT_WIDTH);
  const [rightWidth, setRightWidth] = useState(INIT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);
  //   const [selectedDocTab, setSelectedDocTab] = useState('reference');
  const [leftTopHeight, setLeftTopHeight] = useState(300);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);

  const csWorkspaceState = useAppSelector((state) => state.csWorkspace);

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

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  useEffect(() => {
    const cleanupFns = [
      initResize('left-nav', {
        direction: 'horizontal',
        minWidth: INIT_WIDTH - 100,
        maxWidth: MAX_WIDTH,
      }),
      initResize('right-panel', {
        direction: 'horizontal',
        minWidth: INIT_WIDTH - 100,
        maxWidth: MAX_WIDTH,
      }),
    ];

    return () => {
      cleanupFns.forEach((cleanup) => cleanup?.());
    };
  }, []);

  const handleResize = (
    e: React.MouseEvent,
    startWidth: number,
    setWidth: (width: number) => void,
    isLeft = true,
  ) => {
    const startX = e.clientX;
    setIsDragging(true);

    const doDrag = (e: MouseEvent) => {
      requestAnimationFrame(() => {
        const delta = e.clientX - startX;
        const newWidth = isLeft ? startWidth + delta : startWidth - delta;
        const minWidth = INIT_WIDTH - 100;
        const maxWidth = isLeft ? MAX_WIDTH : MAX_WIDTH;

        if (newWidth >= minWidth && newWidth <= maxWidth) {
          setWidth(newWidth);
        }
      });
    };

    const stopDrag = () => {
      setIsDragging(false);
      document.removeEventListener('mousemove', doDrag);
      document.removeEventListener('mouseup', stopDrag);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', stopDrag);
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
  };

  useEffect(() => {
    console.info('main page csWorkspaceState:', csWorkspaceState);
  }, [csWorkspaceState]);

  return (
    <div className="customer-service-container">
      <TopNavigation
        identity={{
          href: '/',
          title: t('name'),
        }}
        utilities={[
          {
            type: 'menu-dropdown',
            text: ZH_LANGUAGE_LIST.includes(i18n.language) ? ZH_TEXT : EN_TEXT,
            onItemClick: (item) => {
              changeLanguage(item.detail.id);
            },
            items:
              i18n.language === DEFAULT_ZH_LANG
                ? [...LANGUAGE_ITEMS].reverse()
                : LANGUAGE_ITEMS,
          },
          {
            type: 'menu-dropdown',
            text: displayName,
            iconName: 'user-profile',
            onItemClick: () => {},
            items: [{ id: 'signout', text: t('signOut') }],
          },
        ]}
      />

      <div className={`workspace ${isDragging ? 'dragging' : ''}`}>
        <div className="left-nav" style={{ width: leftWidth }}>
          <div className="chat-list" style={{ height: leftTopHeight }}>
            <div className="section-header">
              <h3>Recent Chats</h3>
              <span className="counter">3 new</span>
            </div>
            <div className="chat-items">
              {[
                {
                  id: 1,
                  name: 'Sarah Wilson',
                  message: 'I need help with my order #12345',
                  time: '2min ago',
                  isNew: true,
                },
                {
                  id: 2,
                  name: 'Mike Johnson',
                  message: 'When will my refund be processed?',
                  time: '15min ago',
                  isNew: true,
                },
                {
                  id: 3,
                  name: 'Emma Davis',
                  message: 'Thanks for your help!',
                  time: '1h ago',
                  isNew: false,
                },
              ].map((chat) => (
                <div
                  key={chat.id}
                  className={`chat-item ${chat.isNew ? 'new' : ''}`}
                >
                  <div className="user-avatar">{chat.name.charAt(0)}</div>
                  <div className="chat-info">
                    <div className="chat-header">
                      <span className="name">{chat.name}</span>
                      <span className="time">{chat.time}</span>
                    </div>
                    <p className="last-message">{chat.message}</p>
                  </div>
                  {chat.isNew && <div className="new-badge" />}
                </div>
              ))}
            </div>
          </div>

          <div
            className="resizer horizontal"
            onMouseDown={(e) => {
              const startY = e.clientY;
              const startHeight = leftTopHeight;
              setIsDragging(true);

              const doDrag = (e: MouseEvent) => {
                requestAnimationFrame(() => {
                  const newHeight = startHeight + (e.clientY - startY);
                  if (newHeight > 200 && newHeight < window.innerHeight - 300) {
                    setLeftTopHeight(newHeight);
                  }
                });
              };

              const stopDrag = () => {
                setIsDragging(false);
                document.removeEventListener('mousemove', doDrag);
                document.removeEventListener('mouseup', stopDrag);
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
              };

              document.addEventListener('mousemove', doDrag);
              document.addEventListener('mouseup', stopDrag);
              document.body.style.cursor = 'ns-resize';
              document.body.style.userSelect = 'none';
            }}
          />

          <div className="current-chat">
            <div className="messages">
              {[
                {
                  id: 1,
                  type: 'customer',
                  text: 'Hello, I need help with my order',
                  time: '14:30',
                },
                {
                  id: 2,
                  type: 'agent',
                  text: "Hi! I'd be happy to help. Could you please provide your order number?",
                  time: '14:31',
                },
                {
                  id: 3,
                  type: 'customer',
                  text: "Sure, it's #12345",
                  time: '14:32',
                },
                {
                  id: 4,
                  type: 'agent',
                  text: 'Thank you! Let me check that for you...',
                  time: '14:33',
                },
              ].map((message) => (
                <div key={message.id} className={`message ${message.type}`}>
                  <div className="message-content">
                    <p>{message.text}</p>
                    <span className="time">{message.time}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="chat-input">
              <textarea placeholder="Type your message..." rows={3} />
              <button className="send-btn">
                <span className="icon">📤</span>
                Send
              </button>
            </div>
          </div>
        </div>

        <div
          className="resizer left"
          onMouseDown={(e) => handleResize(e, leftWidth, setLeftWidth)}
        />

        <div className="main-content">
          <div className="profile-header">
            <div className="profile-info">
              <div className="avatar">JD</div>
              <div className="details">
                <h2>John Doe</h2>
                <div className="contact-info">
                  <span>
                    <i className="icon">📱</i> +1 234 567 8900
                  </span>
                  <span>
                    <i className="icon">✉️</i> john.doe@example.com
                  </span>
                  <span>
                    <i className="icon">🆔</i> ACC-12345678
                  </span>
                </div>
                <div className="tags">
                  <span className="tag">Premium Customer</span>
                  <span className="tag">Since 2020</span>
                </div>
              </div>
            </div>
            <div className="profile-actions">
              <button className="action-button">
                <span className="icon">📝</span>
                Edit Profile
              </button>
              <button className="action-button">
                <span className="icon">📋</span>
                View History
              </button>
            </div>
          </div>

          <div className="docs-section">
            <div className="docs-header">
              <h3>Reference Documents</h3>
              <div className="search-box">
                <input type="text" placeholder="Search in documents..." />
              </div>
            </div>
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
                      <h2>
                        {documents.find((d) => d.id === activeDocId)?.title}
                      </h2>
                      <span className="last-modified">
                        Last modified:{' '}
                        {
                          documents.find((d) => d.id === activeDocId)
                            ?.lastModified
                        }
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
          </div>
        </div>

        <div
          className="resizer right"
          onMouseDown={(e) => handleResize(e, rightWidth, setRightWidth, false)}
        />

        <div className="right-panel" style={{ width: rightWidth }}>
          <div className="panel-header">
            <h3>Amazon Q</h3>
            <button className="close-btn">×</button>
          </div>
          <div className="panel-content">
            <ChatMessage />
          </div>
        </div>
      </div>
    </div>
  );
};

export default CustomerService;
