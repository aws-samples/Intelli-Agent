import {
  Box,
  ColumnLayout,
  Container,
  Header,
} from '@cloudscape-design/components';
import React from 'react';
import { useTranslation } from 'react-i18next';

const BenefitsFeatures: React.FC = () => {
  const { t } = useTranslation();
  return (
    <Container
      header={<Header variant="h3">{t('featuresAndBenefits.name')}</Header>}
    >
      <ColumnLayout columns={2} variant="text-grid">
        {[1, 2].map((item) => {
        // {[1, 2, 3, 4].map((item) => {  
          return (
            <div key={item}>
              <Box variant="awsui-key-label">
                {t('featuresAndBenefits.feat' + item + '.name')}
              </Box>
              <div>{t('featuresAndBenefits.feat' + item + '.desc')}</div>
            </div>
          );
        })}
      </ColumnLayout>
    </Container>
  );
};

export default BenefitsFeatures;
