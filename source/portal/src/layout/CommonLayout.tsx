import React, { useContext, useEffect, useState } from 'react';
import {
  AppLayout,
  Flashbar,
  FlashbarProps,
  SideNavigation,
  Spinner,
} from '@cloudscape-design/components';
import { I18nProvider } from '@cloudscape-design/components/i18n';
import messages from '@cloudscape-design/components/i18n/messages/all.en';
import TopNavigation from '@cloudscape-design/components/top-navigation';
import { useTranslation } from 'react-i18next';
import {
  ADITIONAL_SETTINGS,
  ENABLE_TRACE,
  CURRENT_CHAT_BOT,
  DEFAULT_ZH_LANG,
  EN_TEXT,
  LANGUAGE_ITEMS,
  ZH_LANGUAGE_LIST,
  ZH_TEXT,
  USE_CHAT_HISTORY,
  ONLY_RAG_TOOL,
  SCENARIO,
  MODEL_OPTION,
  MAX_TOKEN,
  TEMPERATURE,
} from 'src/utils/const';
import { useAuth } from 'react-oidc-context';
import ConfigContext from 'src/context/config-context';
import { useLocation, useNavigate } from 'react-router-dom';
import CustomBreadCrumb, { BreadCrumbType } from './CustomBreadCrumb';
import { CustomNavigationItem } from 'src/types';
const STORAGE_KEYS = [
  CURRENT_CHAT_BOT,
  USE_CHAT_HISTORY,
  ENABLE_TRACE,
  ONLY_RAG_TOOL,
  SCENARIO,
  MODEL_OPTION,
  MAX_TOKEN,
  TEMPERATURE,
  ADITIONAL_SETTINGS,
];

interface CommonLayoutProps {
  activeHref: string;
  children: React.ReactNode;
  flashBar?: FlashbarProps.MessageDefinition[];
  breadCrumbs?: BreadCrumbType[];
  isLoading?: boolean;
}

const CommonLayout: React.FC<CommonLayoutProps> = ({
  children,
  flashBar,
  breadCrumbs,
  isLoading,
}) => {
  const { t, i18n } = useTranslation();
  const auth = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [fullLogoutUrl, setFullLogoutUrl] = useState('');
  const config = useContext(ConfigContext);
  const navigate = useNavigate();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  const clearStorage = () => {
    STORAGE_KEYS.forEach((key) => {
      localStorage.removeItem(key);
    });
  };

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

  const baseItems = [
    {
      type: 'link',
      text: t('chatbotManagement'),
      href: '/chatbot-management',
    },
    {
      type: 'link',
      text: t('intention'),
      href: '/intention',
    },
  ];

  const promptItem = {
    type: 'link',
    text: t('prompt'),
    href: '/prompts',
  };

  const kbItem =
    config?.kbEnabled === 'true'
      ? {
          type: 'link',
          text: t('docLibrary'),
          href: '/library',
        }
      : null;

  const layoutItems = kbItem
    ? [...baseItems, kbItem, promptItem]
    : [...baseItems, promptItem];
  const location = useLocation();
  const currentActiveHref = location.pathname;

  return (
    <I18nProvider locale={i18n.language} messages={[messages]}>
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
      <AppLayout
        notifications={<Flashbar items={flashBar ?? []} />}
        breadcrumbs={
          breadCrumbs ? (
            <CustomBreadCrumb breadcrumbItems={breadCrumbs} />
          ) : undefined
        }
        navigation={
          <SideNavigation
            activeHref={currentActiveHref}
            header={{ href: '/', text: t('name') }}
            className="main-navigation"
            onFollow={(e) => {
              if (!e.detail.external) {
                e.preventDefault();
                navigate(e.detail.href);
              }
            }}
            items={
              [
                {
                  type: 'link',
                  text: t('homeSidebar'),
                  href: '/',
                  id: 'home-sidebar',
                  itemID: 'home-nav',
                },
                {
                  type: 'section',
                  text: t('chatSpace'),
                  id: 'chat-space',
                  items: [
                    {
                      type: 'link',
                      text: t('chat'),
                      href: '/chats',
                      id: 'chat',
                      itemID: 'chat-nav',
                    },
                    {
                      type: 'link',
                      text: t('sessionHistory'),
                      href: '/sessions',
                      id: 'session-history',
                      itemID: 'session-history-nav',
                    },
                  ],
                },
                {
                  type: 'section',
                  text: t('settings'),
                  items: layoutItems.map((item, index) => ({
                    ...item,
                    itemID: `settings-nav-${index}`,
                    className: item.text.toLowerCase().replace(/\s+/g, '-'),
                  })),
                },
                {
                  type: 'link',
                  text: t('workspace'),
                  href: '/workspace',
                  id: 'workspace',
                  itemID: 'workspace-nav',
                },
                { type: 'divider' },
                {
                  type: 'link',
                  text: t('documentation'),
                  href: 'https://github.com/aws-samples/Intelli-Agent',
                  external: true,
                  itemID: 'docs-nav',
                },
              ] as CustomNavigationItem[]
            }
          />
        }
        content={<>{isLoading ? <Spinner /> : children}</>}
      />
    </I18nProvider>
  );
};

export default CommonLayout;
