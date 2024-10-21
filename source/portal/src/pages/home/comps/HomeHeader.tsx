import { Button, Header, SpaceBetween } from '@cloudscape-design/components';
import React from 'react';
import { useTranslation } from 'react-i18next';

const HomeHeader: React.FC = () => {
  const { t } = useTranslation();
  return (
    <Header
      variant="h1"
      actions={
        <SpaceBetween size="xs" direction="horizontal">
          <Button
            variant="primary"
            onClick={() => {
              // setOpenCreate(true);
            }}
          >
            {t('button.createProject')}
          </Button>
        </SpaceBetween>
      }
      description={t('home:header.desc')}
    >
      {t('solutionName')}
    </Header>
  );
};

export default HomeHeader;
