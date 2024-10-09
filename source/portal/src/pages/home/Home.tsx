import {
  Box,
  Button,
  ContentLayout,
  Grid,
  Header,
  SpaceBetween,
} from '@cloudscape-design/components';
import React from 'react';
import { useTranslation } from 'react-i18next';
import CommonLayout from 'src/layout/CommonLayout';
import GetStarted from './comps/GetStarted';
import MoreResource from './comps/MoreResource';
import BenefitsFeatures from './comps/BenefitsFeatures';
import UseCases from './comps/UseCases';
import BANNER from 'src/assets/images/banner.jpeg';
import { useNavigate } from 'react-router-dom';

const Home: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <CommonLayout toolsHide activeHref="/home" headerVariant="high-contrast">
      <ContentLayout
        headerVariant="high-contrast"
        header={
          <div>
            <Box variant="p">
              {t('awsSolutionGuidance')} | {t('mead')}
            </Box>
            <Header
              variant="h1"
              actions={
                <SpaceBetween size="xs" direction="horizontal">
                  <Button
                    iconName="add-plus"
                    iconAlign="right"
                    variant="primary"
                    onClick={() => {
                      navigate('/chats');
                    }}
                  >
                    {t('button.startToChat')}
                  </Button>
                </SpaceBetween>
              }
              description={t('projectDescription')}
            >
              <Box variant="h1">{t('solutionName')}</Box>
              <Box fontSize="heading-l">{t('subTitle')}</Box>
            </Header>
          </div>
        }
      >
        <div className="pb-30">
          <Grid
            gridDefinition={[
              { colspan: { l: 8, m: 8, default: 8 } },
              { colspan: { l: 4, m: 4, default: 4 } },
            ]}
          >
            <SpaceBetween direction="vertical" size="l">
              <div className="home-banner">
                <img alt="banner" src={BANNER} width="100%" />
              </div>
              <BenefitsFeatures />
              <UseCases />
            </SpaceBetween>
            <SpaceBetween direction="vertical" size="l">
              <GetStarted />
              <MoreResource />
            </SpaceBetween>
          </Grid>
        </div>
      </ContentLayout>
    </CommonLayout>
  );
};

export default Home;
