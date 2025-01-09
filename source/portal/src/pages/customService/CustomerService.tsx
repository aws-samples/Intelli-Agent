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
import UserChatList from './comps/UserChatList';
import ReferenceDocuments from './comps/ReferenceDocuments';
import UserMessage from './comps/UserMessage';

const INIT_WIDTH = 400;
const MAX_WIDTH = 800;

const CustomerService: React.FC = () => {
  const { t, i18n } = useTranslation();
  const displayName = 'Ning';
  const [leftWidth, setLeftWidth] = useState(INIT_WIDTH);
  const [rightWidth, setRightWidth] = useState(INIT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);
  //   const [selectedDocTab, setSelectedDocTab] = useState('reference');
  const [leftTopHeight, setLeftTopHeight] = useState(300);

  const csWorkspaceState = useAppSelector((state) => state.csWorkspace);

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
          <UserChatList leftTopHeight={leftTopHeight} />
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
            <UserMessage />
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
            <ReferenceDocuments />
          </div>
        </div>

        <div
          className="resizer right"
          onMouseDown={(e) => handleResize(e, rightWidth, setRightWidth, false)}
        />

        <div className="right-panel" style={{ width: rightWidth }}>
          <div className="panel-header">
            <h3>Amazon Q</h3>
            <button className="close-btn"></button>
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
