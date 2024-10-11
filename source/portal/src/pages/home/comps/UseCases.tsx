import {
  Box,
  ColumnLayout,
  Container,
  Header,
} from '@cloudscape-design/components';
import React from 'react';
import { useTranslation } from 'react-i18next';

const UseCases: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div className="mt-20">
      <Container header={<Header variant="h2">{t('useCases.name')}</Header>}>
        <ColumnLayout columns={1} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">{t('useCases.case1.name')}</Box>
            <div>{t('useCases.case1.desc')}</div>
          </div>
        </ColumnLayout>
      </Container>
    </div>
  );
};

export default UseCases;
