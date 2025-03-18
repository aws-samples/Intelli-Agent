import {
  Button,
  FormField,
  Grid,
  Input,
  Link,
  SpaceBetween,
} from '@cloudscape-design/components';
import { FC, useContext, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import yaml from 'yaml';
import './style.scss';
import { EN_LANG, OIDC_STORAGE, ROUTES, ZH_LANG, ZH_LANGUAGE_LIST } from 'src/utils/const';
import { useTranslation } from 'react-i18next';
import { changeLanguage, removeKeysWithPrefix } from 'src/utils/utils';
import { confirmSignIn, fetchAuthSession, getCurrentUser, signIn } from '@aws-amplify/auth';
import { Amplify } from 'aws-amplify';
import ConfigContext from 'src/context/config-context';
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
  const [lang, setLang] = useState('');
  const [oldPassError, setOldPassError] = useState('' as string);
  const [newPassError, setNewPassError] = useState('' as string);
  const [confirmPassError, setConfirmPassError] = useState('' as string);
  const builtInConfig = useContext(ConfigContext);
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
    redirectUri: location.state?.redirectUri,
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
      setOldPassError(t('auth:changePWD.requireOldPassword'));
      return;
    }
    setOldPassError('');
    setOldPass(target);
  };

  const changeNewPass = (target: string) => {
    if (target === null || target === '') {
      setNewPass(target);
      setNewPassError(t('auth:changePWD.requireNewPassword'));
      return;
    }
    setNewPassError('');
    setNewPass(target);
  };

  const changeConfirmPass = (target: string) => {
    if (target !== newPass) {
      setConfirmPass(target);
      setConfirmPassError(t('auth:changePWD.requireConfirmPassword'));
      return;
    }
    setConfirmPassError('');
    setConfirmPass(target);
  };

  const handleSignIn = async (username: string, password: string, newPass: string) => {
    try {
      const user: any = await signIn({ username, password });
      console.log('User signed in:', user);
      if (!user.isSignedIn && user.nextStep.signInStep === "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED") {
        console.log('Temporary password expired, resetting to new password...');
        await confirmSignIn({challengeResponse: newPass});
        // await Auth.signOut(); 
        return "success!";
      }
      return user;
    } catch (error: any) {
    if (
      error.name === 'NotAuthorizedException' &&
      error.message.includes('Temporary password has expired and must be reset by an administrator.')
    ) {
        console.log('Temporary password expired, attempting to reset password...');
        setError(t('auth:changePWD.invalidTempPassword'));
        return null;
      }
      setError(error.message);
      return null;
    }
  };
  

  const changePWD = async () => {
    let res
    if (error !== '' || confirmPassError !== '') return;
    if (newPass === '') {
      setNewPassError('New password is required.');
      return;
    }

    try {
      Amplify.configure({
        Auth: {
          Cognito: {
            userPoolId: builtInConfig?.oidcPoolId || '',
            userPoolClientId: builtInConfig?.oidcClientId || ''
          },
        },
      });
      await fetchAuthSession();
      res = await getCurrentUser();

    } catch (error) {
      console.log('User session expired, signing in again...');
      res = await handleSignIn(params.username, oldPass, newPass);

      if (res){
        console.log("password changed successfully, navigate to home page...")
        // let session = fetchAuthSession()
        const currentUser = await getCurrentUser()
        console.log("!!!!!!!current user: ", currentUser)
        let session = currentUser.signInDetails
        localStorage.setItem(
          OIDC_STORAGE,
          JSON.stringify({
            username: params.username,
            provider: params.provider,
            clientId: params.clientId,
            redirectUri: params.redirectUri,
          }),
        );
        localStorage.setItem(
          `oidc.${params.provider}.${params.clientId}`,
          JSON.stringify({
            accessToken: session.tokens?.accessToken.toString(),
            idToken: session.tokens?.idToken?.toString(),
            username: session.tokens?.signInDetails?.loginId
          }),
        );
        removeKeysWithPrefix("CognitoIdentityServiceProvider")
        
        navigate(ROUTES.Home);
        // navigate(ROUTES.Login)
      } else {
        console.log("password changed failed!")
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
              {/* <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}>
                <FormField description="" label={t('auth:changePWD.loginType')}>
                  {params.loginType} - {params.provider}
                </FormField>
                <FormField
                  description=""
                  label={t('auth:changePWD.currentUser')}
                >
                  {params.username}
                </FormField>
              </Grid> */}
              {
                <div style={{ marginTop: 15 }}>
                  <SpaceBetween size={'m'} direction="vertical">
                  <FormField
                      // description={t('auth:changePWD.oldPWDDesc')}
                      label={t('auth:changePWD.oldPWD')}
                      errorText={oldPassError}
                    >
                      <Input
                        value={oldPass}
                        placeholder={t('auth:changePWD.oldPWDDesc')}
                        type='password'
                        onChange={({ detail }) => changeOldPass(detail.value)}
                      />
                    </FormField>
                    {/* <Grid gridDefinition={[{ colspan: 6 }, { colspan: 6 }]}> */}
                    <FormField
                      // description={t('auth:changePWD.newPWDDesc')}
                      label={t('auth:changePWD.newPWD')}
                      errorText={newPassError}
                    >
                      <Input
                        value={newPass}
                        type='password'
                        placeholder={t('auth:changePWD.newPWDDesc')}
                        onChange={({ detail }) => changeNewPass(detail.value)}
                      />
                    </FormField>
                    <FormField
                      // description={t('auth:changePWD.confirmPWDDesc')}
                      label={t('auth:changePWD.confirmPWD')}
                      errorText={confirmPassError}
                    >
                      <Input
                        value={confirmPass}
                        type='password'
                        placeholder={t('auth:changePWD.confirmPWDDesc')}
                        onChange={(event) =>
                          changeConfirmPass(event.detail.value)
                        }
                      />
                    </FormField>
                    {/* </Grid> */}
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
            <div
                style={{
                  marginTop: 10,
                  fontFamily:'Open Sans',
                  fontSize: 14,
                  textAlign: 'right',
                  color: 'red',
                  fontWeight: 800,
                  height: 16,
                }}
              >
                {error}
              </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChangePWD;
// const respondToNewPasswordChallenge = async (
//   session: any,
//   region: string,
//   clientId: string,
//   username: any,
//   newPass: string,
// ) => {
//   const params = {
//     ChallengeName: ChallengeNameType.NEW_PASSWORD_REQUIRED,
//     ClientId: clientId,
//     Session: session,
//     ChallengeResponses: {
//       USERNAME: username,
//       NEW_PASSWORD: newPass,
//     },
//   };
//   const client = new CognitoIdentityProviderClient({
//     region,
//   });
//   const command = new RespondToAuthChallengeCommand(params);
//   return await client.send(command);
// };
