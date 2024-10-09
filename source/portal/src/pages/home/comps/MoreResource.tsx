import { Box, Container, Header, Link } from '@cloudscape-design/components';
import React from 'react';
import { useTranslation } from 'react-i18next';

const MoreResource: React.FC = () => {
  const { t } = useTranslation();
  return (
    <Container header={<Header variant="h2">{t('moreResources.name')}</Header>}>
      <Box padding={{ vertical: 'xs' }}>
        <Link href="/" target="_blank">
          {t('moreResources.faq')}
        </Link>
      </Box>
      <Box padding={{ vertical: 'xs' }}>
        <Link href="/" target="_blank">
          {t('moreResources.submitIssue')}
        </Link>
      </Box>
    </Container>
  );
};

export default MoreResource;
