import React, { useState, useEffect, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import { TopNavigation } from '@cloudscape-design/components';
import {
  ADITIONAL_SETTINGS,
  CURRENT_CHAT_BOT,
  DEFAULT_ZH_LANG,
  EN_TEXT,
  ENABLE_TRACE,
  LANGUAGE_ITEMS,
  MAX_TOKEN,
  MODEL_OPTION,
  ONLY_RAG_TOOL,
  MODEL_TYPE,
  TEMPERATURE,
  USE_CHAT_HISTORY,
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
import { formatTime } from 'src/utils/utils';
import ConfigContext from 'src/context/config-context';
import { useAuth } from 'react-oidc-context';

const INIT_WIDTH = 400;
const MAX_WIDTH = 800;

const STORAGE_KEYS = [
  CURRENT_CHAT_BOT,
  USE_CHAT_HISTORY,
  ENABLE_TRACE,
  ONLY_RAG_TOOL,
  MODEL_TYPE,
  MODEL_OPTION,
  MAX_TOKEN,
  TEMPERATURE,
  ADITIONAL_SETTINGS,
];

const CustomerService: React.FC = () => {
  const { t, i18n } = useTranslation();
  const config = useContext(ConfigContext);
  const auth = useAuth();
  const [leftWidth, setLeftWidth] = useState(INIT_WIDTH);
  const [rightWidth, setRightWidth] = useState(INIT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);
  const [fullLogoutUrl, setFullLogoutUrl] = useState('');
  const [displayName, setDisplayName] = useState('');

  const clearStorage = () => {
    STORAGE_KEYS.forEach((key) => {
      localStorage.removeItem(key);
    });
  };
  //   const [selectedDocTab, setSelectedDocTab] = useState('reference');
  const [leftTopHeight, setLeftTopHeight] = useState(300);

  const csWorkspaceState = useAppSelector((state) => state.csWorkspace);

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  useEffect(() => {
    if (ZH_LANGUAGE_LIST.includes(i18n.language)) {
      changeLanguage(DEFAULT_ZH_LANG);
    }
    if (config?.oidcLogoutUrl) {
      const redirectUrl = config?.oidcRedirectUrl.replace('/signin', '');
      const queryParams = new URLSearchParams({
        client_id: config.oidcClientId,
        id_token_hint: auth.user?.id_token ?? '',
        logout_uri: redirectUrl,
        redirect_uri: redirectUrl,
        post_logout_redirect_uri: redirectUrl,
      });
      const logoutUrl = new URL(config?.oidcLogoutUrl);
      logoutUrl.search = queryParams.toString();
      setFullLogoutUrl(decodeURIComponent(logoutUrl.toString()));
    }
  }, []);

  useEffect(() => {
    setDisplayName(
      auth.user?.profile?.email ||
        auth.user?.profile?.name ||
        auth.user?.profile?.preferred_username ||
        auth.user?.profile?.nickname ||
        auth.user?.profile?.sub ||
        '',
    );
  }, [auth]);

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
              // window.location.reload();
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
            onItemClick: (item) => {
              if (item.detail.id === 'signout') {
                if (fullLogoutUrl) {
                  auth.removeUser();
                  clearStorage();
                  window.location.href = fullLogoutUrl;
                }
                auth.removeUser();
              }
            },
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
              <div className="avatar">
                {csWorkspaceState.currentUser?.userName.charAt(0)}
              </div>
              <div className="details">
                <h2>{csWorkspaceState.currentUser?.userName}</h2>
                <div className="contact-info">
                  <span>
                    <i className="icon">📱</i>{' '}
                    {csWorkspaceState.currentUser?.status}
                  </span>
                  <span>
                    <i className="icon">✉️</i>{' '}
                    {csWorkspaceState.currentUser?.userName}
                  </span>
                  <span>
                    <i className="icon">🆔</i>{' '}
                    {csWorkspaceState.currentUser?.clientType}
                  </span>
                </div>
                <div className="tags">
                  <span className="tag">Premium Customer</span>
                  <span className="tag">
                    Since{' '}
                    {formatTime(
                      csWorkspaceState.currentUser?.createTimestamp ?? 0,
                    )}
                  </span>
                </div>
              </div>
            </div>
            {/* <div className="profile-actions">
              <button className="action-button">
                <span className="icon">📝</span>
                Edit Profile
              </button>
              <button className="action-button">
                <span className="icon">📋</span>
                View History
              </button>
            </div> */}
          </div>

          <div className="docs-section">
            <div className="docs-header">
              <h3>{t('referenceDocuments')}</h3>
              <div className="search-box">
                {/* <input type="text" placeholder="Search in documents..." /> */}
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
            <h3>{t('name')}</h3>
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
