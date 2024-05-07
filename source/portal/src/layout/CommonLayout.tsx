import React, { useEffect } from 'react';
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
  DEFAULT_ZH_LANG,
  EN_TEXT,
  LANGUAGE_ITEMS,
  ZH_LANGUAGE_LIST,
  ZH_TEXT,
} from 'src/utils/const';

interface CommonLayoutProps {
  activeHref: string;
  children: React.ReactNode;
  flashBar?: FlashbarProps.MessageDefinition[];
  breadCrumbs?: React.ReactNode;
  isLoading?: boolean;
}

const CommonLayout: React.FC<CommonLayoutProps> = ({
  activeHref,
  children,
  flashBar,
  breadCrumbs,
  isLoading,
}) => {
  const { t, i18n } = useTranslation();
  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  useEffect(() => {
    if (ZH_LANGUAGE_LIST.includes(i18n.language)) {
      changeLanguage(DEFAULT_ZH_LANG);
    }
  }, []);

  return (
    <I18nProvider locale={i18n.language} messages={[messages]}>
      <TopNavigation
        identity={{
          href: '#',
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
            text: 'User Name',
            description: 'email@example.com',
            iconName: 'user-profile',
            items: [
              { id: 'profile', text: 'Profile' },
              { id: 'signout', text: 'Sign out' },
            ],
          },
        ]}
      />
      <AppLayout
        notifications={<Flashbar items={flashBar ?? []} />}
        breadcrumbs={breadCrumbs}
        navigation={
          <SideNavigation
            activeHref={activeHref}
            header={{ href: '#/', text: t('name') }}
            items={[
              {
                type: 'section',
                text: 'Chat Space',
                items: [
                  {
                    type: 'link',
                    text: 'Chat Bot',
                    href: '/',
                  },
                ],
              },
              {
                type: 'section',
                text: 'Settings',
                items: [
                  {
                    type: 'link',
                    text: 'Docs Library',
                    href: '/library',
                  },
                ],
              },
              { type: 'divider' },
              {
                type: 'link',
                text: 'Documentation',
                href: 'https://example.com',
                external: true,
              },
            ]}
          />
        }
        content={<>{isLoading ? <Spinner /> : children}</>}
      />
    </I18nProvider>
  );
};

export default CommonLayout;
