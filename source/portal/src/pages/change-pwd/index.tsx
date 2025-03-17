import {
  Button,
  FormField,
  Grid,
  Input,
  Link,
  SpaceBetween,
} from '@cloudscape-design/components';
import {
  ChallengeNameType,
  CognitoIdentityProviderClient,
  RespondToAuthChallengeCommand,
} from '@aws-sdk/client-cognito-identity-provider';
import { FC, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import yaml from 'yaml';
import './style.scss';
import { EN_LANG, ROUTES, ZH_LANG, ZH_LANGUAGE_LIST } from 'src/utils/const';
import { useTranslation } from 'react-i18next';
import { changeLanguage } from 'src/utils/utils';
import { fetchAuthSession, getCurrentUser, signIn, updatePassword } from '@aws-amplify/auth';
// import { changePassword, currentAuthenticatedUser } from '@aws-amplify/auth';
// import { Auth } from '@aws-amplify/auth';

const ChangePWD: FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  // const { t } = useTranslation();
  const { t, i18n } = useTranslation();
  const [projectName, setProjectName] = useState('' as string);
  const [oldPass, setOldPass] = useState('' as string);
  const [newPass, setNewPass] = useState('' as string);
  const [error, setError] = useState('' as string);
  const [confirmPass, setConfirmPass] = useState('' as string);
  const [confirmPassError, setConfirmPassError] = useState('' as string);
  const [lang, setLang] = useState('');
  // const [reasonTxt, setReasonTxt] = useState("" as string);
  // const [items, setItems] = useState([] as any[]);
  // const [config]=useState(null as any);
  // const [isLoading, setIsloading] = useState(true)
  const params = {
    session: location.state?.session,
    username: location.state?.username,
    reason: location.state?.reason,
    loginType: location.state?.loginType,
    provider: location.state?.provider,
    author: location.state?.author,
    thirdLogin: location.state?.thirdLogin,
    region: location.state?.region,
    clientId: location.state?.clientId,
  };

  useEffect(() => {
    if (ZH_LANGUAGE_LIST.includes(i18n.language)) {
      setLang(ZH_LANG);
      i18n.changeLanguage(ZH_LANG);
    } else {
      setLang(EN_LANG);
      i18n.changeLanguage(EN_LANG);
    }

    const loadConfig = async () => {
      let response = await fetch('/config.yaml');
      let data = await response.text();
      return yaml.parse(data);
    };
    loadConfig().then((configData) => {
      setProjectName(configData.project);
    });
  }, []);
  const toLogin = () => {
    navigate(ROUTES.Login);
  };

  const toRegister = () => {
    navigate(ROUTES.Register);
  };

  const changeOldPass = (target: string) => {
    if (target === null || target === '') {
      setOldPass(target);
      setError('Old password is required.');
      return;
    }
    setError('');
    setOldPass(target);
  };

  const changeNewPass = (target: string) => {
    if (target === null || target === '') {
      setNewPass(target);
      setError('New password is required.');
      return;
    }
    setError('');
    setNewPass(target);
  };

  const changeConfirmPass = (target: string) => {
    if (target !== newPass) {
      setConfirmPass(target);
      setConfirmPassError('The two entered passwords do not match.');
      return;
    }
    setConfirmPassError('');
    setConfirmPass(target);
  };

  const handleSignIn = async (username: string, password: string) => {
    try {
      const user = await signIn({ username, password });
      console.log('User signed in:', user);
      return user;
    } catch (error: any) {
      // NotAuthorizedException: Temporary password has expired and must be reset by an administrator.
      if(error.name === "NotAuthorizedException" && error.message.includes("Temporary password has expired and must be reset by an administrator.")){
        console.error('Sign-in failed:', error);
        return null;
      } else {
        console.error('Sign-in failed:', error);
        return null;
      }
      }
  };
  

  const changePWD = async () => {
    let user;
    if (error !== '' || confirmPassError !== '') return;
    if (newPass === '') {
      setError('New password is required.');
      return;
    }

    try {
      // Step 1: Check if the user has a valid session
      await fetchAuthSession();
      user = await getCurrentUser();
      
      // Step 2: If user is not authenticated, prompt login
    } catch (error) {
      console.log('User session expired, signing in again...');
      user = await handleSignIn(params.username, oldPass);
      if (!user) return; // Stop if login fails
    }

    try {
      // await fetchAuthSession();
      // const user = await getCurrentUser();
      // console.log('User fetch successfully:', user);
      const response = await updatePassword({oldPassword: oldPass, newPassword: newPass});
      console.log('Password updated successfully:', response);
    } catch (error: any) {
      console.error("Error updating password:", error);
      if (error.name === 'UserUnAuthenticatedException') {
        setError('Please sign in again.');
      }
    }
  };

  return (
    <div className="changepwd-div">
      <div className="container">
        {/* <img src={banner} alt='banner' className='banner'/> */}
        <div className="banner">{projectName}</div>
        <div className="sub-title">
          {t('auth:support-prefix')} {params.author} {t('auth:support-postfix')}{' '}
          <Link
            variant="info"
            onFollow={() => changeLanguage(lang, setLang, i18n)}
          >
            {t('auth:changeLang')}
          </Link>
        </div>
        <div className="tab" style={{ paddingLeft: '10%' }}>
          <div style={{ height: 320, width: '90%' }}>
            <div className="action">
              {t('auth:changePassword')}{' '}
              <span className="reason">
                (
                {params.reason === 'first-login'
                  ? t('auth:changePWDByFirstLogin')
                  : t('auth:userChange')}
                )
              </span>
            </div>
            <div style={{ width: '100%' }}>
              <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                <FormField description="" label={t('auth:changePWD.loginType')}>
                  {params.loginType} - {params.provider}
                </FormField>
                <FormField
                  description=""
                  label={t('auth:changePWD.currentUser')}
                >
                  {params.username}
                </FormField>
              </Grid>
              {
                <div style={{ marginTop: 15 }}>
                  <SpaceBetween size={'m'} direction="vertical">
                  <FormField
                      description={t('auth:changePWD.oldPWDDesc')}
                      label={t('auth:changePWD.oldPWD')}
                      errorText={error}
                    >
                      <Input
                        value={oldPass}
                        placeholder={t('auth:changePWD.oldPWDDesc')}
                        onChange={({ detail }) => changeOldPass(detail.value)}
                      />
                    </FormField>
                    <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                    <FormField
                      description={t('auth:changePWD.newPWDDesc')}
                      label={t('auth:changePWD.newPWD')}
                      errorText={error}
                    >
                      <Input
                        value={newPass}
                        placeholder={t('auth:changePWD.newPWDDesc')}
                        onChange={({ detail }) => changeNewPass(detail.value)}
                      />
                    </FormField>
                    <FormField
                      description={t('auth:changePWD.confirmPWDDesc')}
                      label={t('auth:changePWD.confirmPWD')}
                      errorText={confirmPassError}
                    >
                      <Input
                        value={confirmPass}
                        placeholder={t('auth:changePWD.confirmPWDDesc')}
                        onChange={(event) =>
                          changeConfirmPass(event.detail.value)
                        }
                      />
                    </FormField>
                    </Grid>
                  </SpaceBetween>
                </div>
              }
            </div>
          </div>
          <div className="bottom-button">
            <Button
              variant="primary"
              className="submit"
              onClick={() => changePWD()}
            >
              {t('auth:changePWD:submit')}
            </Button>
          </div>
          <div
            style={{
              color: 'rgb(128, 128, 128)',
              fontSize: 14,
              marginTop: 30,
              width: '90%',
            }}
          >
            <Grid gridDefinition={[{ colspan: 12 }]}>
              <div style={{ paddingTop: 5, textAlign: 'right' }}>
                <span style={{ color: 'rgb(128, 128, 128)' }}>
                  {t('auth:needAccount')}{' '}
                </span>
                <Link onFollow={toRegister}>{t('auth:register')}</Link>
                <span style={{ color: 'rgb(128, 128, 128)' }}>
                  {' '}
                  {t('auth:or')}{' '}
                </span>
                <Link onFollow={toLogin}>{t('auth:login')}</Link>
              </div>
            </Grid>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChangePWD;
const respondToNewPasswordChallenge = async (
  session: any,
  region: string,
  clientId: string,
  username: any,
  newPass: string,
) => {
  const params = {
    ChallengeName: ChallengeNameType.NEW_PASSWORD_REQUIRED,
    ClientId: clientId,
    Session: session,
    ChallengeResponses: {
      USERNAME: username,
      NEW_PASSWORD: newPass,
    },
  };
  const client = new CognitoIdentityProviderClient({
    region,
  });
  const command = new RespondToAuthChallengeCommand(params);
  return await client.send(command);
};
