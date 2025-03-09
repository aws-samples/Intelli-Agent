import React, { useContext, useEffect, useState } from 'react';
import {
  AppLayout,
  Flashbar,
  FlashbarProps,
  SideNavigation,
  Spinner,
} from '@cloudscape-design/components';
import { jwtDecode } from "jwt-decode";

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
  MODEL_TYPE,
  MODEL_OPTION,
  MAX_TOKEN,
  TEMPERATURE,
  ROUTES,
  OIDC_STORAGE,
  OIDC_PREFIX,
  OIDC_PROVIDER,
} from 'src/utils/const';
// import { useAuth } from 'react-oidc-context';
import ConfigContext from 'src/context/config-context';
import { useLocation, useNavigate } from 'react-router-dom';
import CustomBreadCrumb, { BreadCrumbType } from './CustomBreadCrumb';
import { CustomNavigationItem } from 'src/types';
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
import './layout.scss'
import { logout } from 'src/request/authing';

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
  // const auth = useAuth();
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
    let idToken = ""
    let displayName = "Guest"
    const oidc = localStorage.getItem(OIDC_STORAGE)
    if (oidc) {
      const oidcRes = JSON.parse(oidc)
      const authToken = localStorage.getItem(`${OIDC_PREFIX}${oidcRes.provider}.${oidcRes.clientId}`)
      if (authToken){
        const token = JSON.parse(authToken)
      if(oidcRes.provider === OIDC_PROVIDER.AUTHING){
        idToken = token.id_token
        const idTokenRes: any = jwtDecode(idToken)
        displayName = idTokenRes?.name || idTokenRes?.email || idTokenRes?.nickname || displayName
      } else {
        displayName = token.username
      }}
    }

    if (ZH_LANGUAGE_LIST.includes(i18n.language)) {
      changeLanguage(DEFAULT_ZH_LANG);
    }
    if (config?.oidcLogoutUrl) {
      const redirectUrl = config?.oidcRedirectUrl.replace('/signin', '');
      const queryParams = new URLSearchParams({
        client_id: config.oidcClientId,
        id_token_hint: idToken,
        logout_uri: redirectUrl,
        redirect_uri: redirectUrl,
        post_logout_redirect_uri: redirectUrl,
      });
      const logoutUrl = new URL(config?.oidcLogoutUrl);
      logoutUrl.search = queryParams.toString();
      setDisplayName(displayName);
      setFullLogoutUrl(decodeURIComponent(logoutUrl.toString()));
    }
  }, []);

  const baseItems = [
    {
      type: 'link',
      text: t('chatbotManagement'),
      href: ROUTES.Chatbot,
    },
    {
      type: 'link',
      text: t('intention'),
      href: ROUTES.Intention,
    }
  ];

  const promptItem = {
    type: 'link',
    text: t('prompt'),
    href: ROUTES.Prompt,
  };

  const kbItem =
    config?.kbEnabled === 'true'
      ? {
          type: 'link',
          text: t('docLibrary'),
          href: ROUTES.Library,
        }
      : null;

  const layoutItems = kbItem
    ? [...baseItems, kbItem, promptItem]
    : [...baseItems, promptItem];
  const location = useLocation();
  const currentActiveHref = location.pathname;

  return (
      <>
      <TopNavigation
        i18nStrings={{searchIconAriaLabel: t('menu.search') || '',
          searchDismissIconAriaLabel: t('menu.closeSearch') || '',
          overflowMenuTriggerText: t('menu.more') || '',
          overflowMenuTitleText: t('menu.all') || '',
          overflowMenuBackIconAriaLabel: t('menu.back') || '',
          overflowMenuDismissIconAriaLabel: t('menu.closeMenu') || '',}}
        identity={{
          href: ROUTES.Home,
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
                  // auth.removeUser();
                  clearStorage();
                  logout();
                  window.location.href = fullLogoutUrl;
                }
                // auth.removeUser();
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
            header={{ href: ROUTES.Home, text: t('assetName') }}
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
                  href: ROUTES.Home,
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
                      href: ROUTES.Chat,
                      id: 'chat',
                      itemID: 'chat-nav',
                    },
                    {
                      type: 'link',
                      text: t('sessionHistory'),
                      href: ROUTES.Session,
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
                // {
                //   type: 'link',
                //   text: t('workspace'),
                //   href: '/workspace',
                //   id: 'workspace',
                //   itemID: 'workspace-nav',
                // },
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
      </>
  );
};

export default CommonLayout;
