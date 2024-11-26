import {
  Box,
  Button,
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
import UseCases from './comps/UseCases';
import BANNER from 'src/assets/images/banner.jpeg';
import { useNavigate } from 'react-router-dom';
import Joyride, { CallBackProps, STATUS, ACTIONS } from 'react-joyride';
import ConfigContext from 'src/context/config-context';

const Home: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [runTour, setRunTour] = useState(false);
  const config = useContext(ConfigContext);

  const baseSteps = [
    {
      target: '.home-banner',
      content: 'Deploying this solution using the default parameters will build the environment in Amazon Web Services.',
      disableBeacon: true,
    },
    {
      target: 'a[href="/chats"]',
      content: 'Click here to start chatting with our AI assistant.',
      disableBeacon: true,
    },
    {
      target: 'a[href="/sessions"]',
      content: 'Session history contains all your chat history, you can resume the chat by choosing the chat history',
      disableBeacon: true,
    },
    {
      target: 'a[href="/chatbot-management"]',
      content: 'You can create/edit/delete the chatbots. Each chatbot has at least one index for Intention/QD/QQ, Intention index stores the chatbot intentions, QD index stores the knowledges, QQ index stores the FAQ.',
      disableBeacon: true,
    },
    {
      target: 'a[href="/intention"]',
      content: 'Manage your intentions here. The intentions are uploaded via excel files, the chatbot will chat according to the intentions you provided, if no intention is provided, it will retrive knowledges by default.',
      disableBeacon: true,
    },
  ];

  const kbStep = {
    target: 'a[href="/library"]',
    content: 'You can create/update/delete knowledges. Choose index type as QD to inject a knowledge, and choose QQ index type to inject FAQ (only in excel format)',
    disableBeacon: true,
  };

  const promptsStep = {
    target: 'a[href="/prompts"]',
    content: 'Manage your prompts here. Conversation summary prompt will rewrite the queries in your chat history, RAG prompt is for how to use the retrieved knowledges to help LLM generate responses, tool calling prompt defines how the agent choose and invoke tools.',
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
        scrollToFirstStep={true}
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
          back: 'Previous',
          close: 'Close',
          last: 'Finish',
          next: 'Next',
          skip: 'Skip tour',
        }}
      />
      <CommonLayout activeHref="/home">
        <ContentLayout
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
                    <Button
                      iconName="refresh"
                      variant="normal"
                      onClick={resetTour}
                    >
                      {t('button.restartTour')}
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
    </>
  );
};

export default Home;
