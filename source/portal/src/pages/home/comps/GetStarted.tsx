import { Box, Container, Header, Link } from '@cloudscape-design/components';
import React from 'react';
import { useTranslation } from 'react-i18next';

const GetStarted: React.FC = () => {
  const { t } = useTranslation();
  return (
    <Container
      header={<Header variant="h3">{t('gettingStarted.name')}</Header>}
    >
      {/* <Box padding={{ vertical: 'xs' }}>
        <Link href="/" target="_blank">
          {t('gettingStarted.link1')}
        </Link>
      </Box> */}
      <Box padding={{ vertical: 'xs' }}>
        <Link href="https://amzn-chn.feishu.cn/docx/JSakd9VCBoHrzfx9Gvoctm60nyg" target="_blank">
          {t('gettingStarted.link2')}
        </Link>
      </Box>
      {/* <Box padding={{ vertical: 'xs' }}>
        <Link href="/" target="_blank">
          {t('gettingStarted.link3')}
        </Link>
      </Box> */}
    </Container>
  );
};

export default GetStarted;
