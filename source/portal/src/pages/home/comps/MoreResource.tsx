import { Box, Container, Header, Link } from '@cloudscape-design/components';
import React from 'react';
import { useTranslation } from 'react-i18next';

const MoreResource: React.FC = () => {
  const { t } = useTranslation();
  return (
    <Container header={<Header variant="h3">{t('moreResources.name')}</Header>}>
      <Box padding={{ vertical: 'xs' }}>
        <Link href="https://catalog.us-east-1.prod.workshops.aws/workshops/1ebc087e-17a7-406b-99c1-62a34238a14c" target="_blank">
          {t('moreResources.workshop')}
        </Link>
      </Box>
      <Box padding={{ vertical: 'xs' }}>
        <Link href="https://github.com/aws-samples/Intelli-Agent/issues/new" target="_blank">
          {t('moreResources.submitIssue')}
        </Link>
      </Box>
    </Container>
  );
};

export default MoreResource;
