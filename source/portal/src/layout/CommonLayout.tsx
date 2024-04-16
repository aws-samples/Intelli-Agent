import React from 'react';
import {
  AppLayout,
  Flashbar,
  FlashbarProps,
  SideNavigation,
} from '@cloudscape-design/components';
import { I18nProvider } from '@cloudscape-design/components/i18n';
import messages from '@cloudscape-design/components/i18n/messages/all.en';
import TopNavigation from '@cloudscape-design/components/top-navigation';

const LOCALE = 'en';

interface CommonLayoutProps {
  activeHref: string;
  children: React.ReactNode;
  flashBar?: FlashbarProps.MessageDefinition[];
  breadCrumbs?: React.ReactNode;
}

const CommonLayout: React.FC<CommonLayoutProps> = ({
  activeHref,
  children,
  flashBar,
  breadCrumbs,
}) => {
  return (
    <I18nProvider locale={LOCALE} messages={[messages]}>
      <TopNavigation
        identity={{
          href: '#',
          title: 'AWS LLM Bot',
        }}
        utilities={[
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
            header={{ href: '#/', text: 'AWS LLM Bot' }}
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
        content={children}
      />
    </I18nProvider>
  );
};

export default CommonLayout;
