import {
  Box,
  Button,
  Container,
  ContentLayout,
  Grid,
  Header,
  SpaceBetween,
} from '@cloudscape-design/components';
import React, { useState, useEffect, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import CommonLayout from 'src/layout/CommonLayout';
import GetStarted from './comps/GetStarted';
import MoreResource from './comps/MoreResource';
import BenefitsFeatures from './comps/BenefitsFeatures';
import BANNER from 'src/assets/images/banner.jpeg';
import { useNavigate } from 'react-router-dom';
import Joyride, { CallBackProps, STATUS, ACTIONS } from 'react-joyride';
import ConfigContext from 'src/context/config-context';
import { ROUTES } from 'src/utils/const';

const Home: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [runTour, setRunTour] = useState(false);
  const config = useContext(ConfigContext);

  const baseSteps = [
    {
      target: '.home-banner',
      content: t('tour.home'),
      disableBeacon: true,
    },
    {
      target: `a[href="${ROUTES.Chat}"]`,
      content: t('tour.chat'),
      disableBeacon: true,
    },
    {
      target: `a[href="${ROUTES.Session}"]`,
      content: t('tour.session'),
      disableBeacon: true,
    },
    {
      target: `a[href="${ROUTES.Chatbot}"]`,
      content: t('tour.chatbot'),
      disableBeacon: true,
    },
    {
      target: `a[href="${ROUTES.Intention}"]`,
      content: t('tour.intention'),
      disableBeacon: true,
    }
  ];

  const kbStep = {
    target: `a[href="${ROUTES.Library}"]`,
    content: t('tour.kb'),
    disableBeacon: true,
  };

  const promptsStep = {
    target: `a[href="${ROUTES.Prompt}"]`,
    content: t('tour.prompt'),
    disableBeacon: true,
  };

  const steps = [
    ...baseSteps,
    ...(config?.kbEnabled === 'true' ? [kbStep] : []),
    promptsStep,
  ].filter(step => {
    return document.querySelector(step.target as string) !== null;
  });

  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRunTour(false);
      localStorage.setItem('tourCompleted', 'true');
    } else if (action === ACTIONS.START) {
      setRunTour(true);
    }
  };

  const resetTour = () => {
    localStorage.removeItem('tourCompleted');
    setRunTour(true);
  };

  useEffect(() => {
    const tourCompleted = localStorage.getItem('tourCompleted');
    if (!tourCompleted) {
      setRunTour(true);
    }
  }, []);

  const joyrideStyles = {
    options: {
      zIndex: 9999,
      arrowColor: '#fff',
      backgroundColor: '#fff',
      primaryColor: '#0972d3',
      textColor: '#16191f',
      overlayColor: 'rgba(0, 0, 0, 0.5)',
      width: 400,
    },
    overlay: {
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      mixBlendMode: 'hard-light' as const,
      zIndex: 9998
    },
    tooltip: {
      zIndex: 9999,
      backgroundColor: '#fff',
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
      padding: '16px',
      fontSize: '14px',
      animation: 'fade-in 0.3s ease-in-out',
    },
    tooltipContainer: {
      textAlign: 'left' as const,
      padding: '8px 0',
    },
    tooltipTitle: {
      fontSize: '16px',
      fontWeight: 'bold',
      marginBottom: '8px',
      color: '#16191f',
    },
    tooltipContent: {
      color: '#5f6b7a',
      lineHeight: '1.5',
    },
    buttonNext: {
      backgroundColor: '#0972d3',
      padding: '8px 16px',
      fontSize: '14px',
      fontWeight: '500',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
      transition: 'background-color 0.2s ease',
    },
    buttonBack: {
      color: '#5f6b7a',
      padding: '8px 16px',
      fontSize: '14px',
      fontWeight: '500',
      marginRight: '8px',
      backgroundColor: 'transparent',
      border: 'none',
      cursor: 'pointer',
      transition: 'color 0.2s ease',
    },
    buttonSkip: {
      color: '#5f6b7a',
      fontSize: '14px',
      padding: '8px',
      backgroundColor: 'transparent',
      border: 'none',
      cursor: 'pointer',
      transition: 'color 0.2s ease',
    },
    spotlight: {
      backgroundColor: 'transparent',
      borderRadius: '4px',
      boxShadow: '0 0 0 4px rgba(9, 114, 211, 0.3)',
      zIndex: 9998,
    },
    beacon: {
      display: 'none'
    }
  };

  return (
    <>
      <style>
        {`
          @keyframes fade-in {
            from {
              opacity: 0;
              transform: translateY(10px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}
      </style>
      <Joyride
        steps={steps}
        continuous={true}
        showSkipButton={true}
        callback={handleJoyrideCallback}
        run={runTour}
        scrollToFirstStep={false}
        disableOverlayClose={true}
        hideBackButton={false}
        spotlightClicks={false}
        styles={joyrideStyles}
        floaterProps={{
          styles: {
            options: {
              zIndex: 9999
            },
            arrow: {
              length: 8,
              margin: 4,
            },
            wrapper: {
              padding: 0,
              margin: 0,
              transition: 'transform 0.2s ease-in-out',
            }
          },
          offset: 10,
          wrapperOptions: {
            offset: 0,
            position: true
          }
        }}
        locale={{
          back: t('tour.previous'),
          close: t('tour.close'),
          last: t('tour.finish'),
          next: t('tour.next'),
          skip: t('tour.skip'),
        }}
      />
      <CommonLayout activeHref="/home">
        <ContentLayout
          header={
            <div style={{marginTop:25}}>
              <Box variant="p">
                {t('common:awsSolutionGuidance')} | {t('mead')}
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
                        navigate(ROUTES.Chat);
                      }}
                    >
                      {t('common:button.startToChat')}
                    </Button>
                    <Button
                      iconName="refresh"
                      variant="normal"
                      onClick={resetTour}
                    >
                      {t('tour.restartTour')}
                    </Button>
                  </SpaceBetween>
                }
                description={t('projectDescription')}
              >
                <Box variant="h1">{t('common:solutionName')}</Box>
                {/* <Box fontSize="heading-l">{t('subTitle')}</Box> */}
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
                
                {/* <Container
        className="fix-mid-screen common-header"
      > */}
        {/* <SpaceBet direction='horizontal' size='m'> */}
          {/* <Grid gridDefinition={[{ colspan: 3 }, { colspan: 3 },{colspan: 3},{colspan: 3}]}>
              <div>
                <Box variant="h4" >
                  {t('modelCnt')}
                </Box>
                <Link variant='awsui-value-large' className="no-link">18</Link>
              </div>
              <div>
                <Box variant="h4">{t('docCnt')}</Box>
                <Link variant='awsui-value-large' className="no-link">2</Link>
              </div>
              <div>
                <Box variant="h4">{t('botCnt')}</Box>
                <Link variant='awsui-value-large' className="no-link">3</Link>
              </div>
              <div>
                <Box variant="h4">
                  {t('sessionCnt')}
                </Box>
                <Link variant='awsui-value-large' className="no-link">18</Link>
              </div>
            </Grid> */}
            
            {/* </SpaceBet ween> */}
       
      {/* </Container> */}
      <Container header={<Header variant="h2">{t('architecture')}</Header>}>
                <div className="home-banner">
                  <img alt="banner" src={BANNER} width="100%" />
                </div>
                </Container>
                <BenefitsFeatures />
                {/* <UseCases /> */}
              </SpaceBetween>
              <SpaceBetween direction="vertical" size="l">
                <GetStarted />
                <MoreResource />
              </SpaceBetween>
            </Grid>
          </div>
        </ContentLayout>
      </CommonLayout>
    </>
  );
};

export default Home;
