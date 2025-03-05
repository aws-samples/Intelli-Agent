import {
  Button,
  Checkbox,
  Grid,
  Link,
  SpaceBetween,
  Spinner,
  Tabs,
} from '@cloudscape-design/components';
import { FC, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import yaml from 'yaml';
import OIDC from './component/oidc';
import SNS from './component/sns';
import User from './component/user';
import './style.scss';
import { AxiosError } from 'axios';
import { useTranslation } from 'react-i18next';
import {
  EN_LANG,
  LOGIN_TYPE,
  OIDC_STORAGE,
  ROUTES,
  ZH_LANG,
  ZH_LANGUAGE_LIST,
} from 'src/utils/const';
import useAxiosAuthRequest from 'src/hooks/useAxiosAuthRequest';
import ConfigContext from 'src/context/config-context';
import { Amplify } from 'aws-amplify';
import { signIn } from 'aws-amplify/auth';

const Login: FC = () => {
  const [activeTabId, setActiveTabId] = useState(LOGIN_TYPE.OIDC);
  const [logging, setLogging] = useState(false as boolean);
  const [username, setUsername] = useState(null as any);
  const [password, setPassword] = useState(null as any);
  const [keep, setKeep] = useState(false);
  const navigate = useNavigate();
  // const { i18n } = useTranslation();
  const { t, i18n } = useTranslation();
  const fetchData = useAxiosAuthRequest(i18n.language === 'zh'? "zh-CN" : "en-US");
  const [error, setError] = useState('' as string);
  const [config, setConfig] = useState(null as any);
  const [selectedProvider, setSelectedProvider] = useState(null as any);
  const [selectedProviderName, setSelectedProviderName] = useState(null as any);
  const [tabs, setTabs] = useState([] as any[]);
  const [projectName, setProjectName] = useState('' as string);
  const [author, setAuthor] = useState('' as string);
  const [version, setVersion] = useState(0);
  const [lang, setLang] = useState('');
  const [isLoading, setIsloading] = useState(true as boolean);
  const [oidcList, setOidcList] = useState([] as any[]);
  const oidcOptions: any[] = [];
  const builtInConfig = useContext(ConfigContext);

  // useEffect(() => {
  //   const listener = (data: any) => {
  //     const { payload } = data;
  //     if (payload.event === "signInWithRedirect") {
  //       console.log("signInWithRedirect:", payload.data);
  //     } else if (payload.event === "signedIn") {
  //       console.log("User signed in successfully:", payload.data);
  //       const fetchUserDetails = async ()=>{
  //         const currentUser = await fetchUserAttributes();
  //         console.log('Current user:', currentUser);
  //         localStorage.setItem(USER, currentUser.email||currentUser.username||currentUser.name||"anonymous user");
  //       }
  //       const fetchSessionDetails = async ()=>{
  //         const currentSession = await fetchAuthSession();
  //         localStorage.setItem(`${OIDC_PREFIX}midway`, JSON.stringify({ access_token: currentSession.tokens?.accessToken.toString(), id_token: currentSession.tokens?.idToken?.toString() }));
  //         localStorage.setItem(OIDC_STORAGE, "midway");
  //         navigate(ROUTES.Home);
  //       }
  //       fetchUserDetails();
  //       fetchSessionDetails()
  //     } else if(payload.event === "signInWithRedirect_failure"){
  //       console.log("signInWithRedirect_failure:", payload.data);
  //     }
  //   };
  //   Hub.listen("auth", listener);
  // }, []);

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
      setConfig(configData);
    });
    setError('');
  }, [i18n]);

  useEffect(() => {
    updateEnv(config);
  }, [config, username, password, lang, selectedProvider]);

  const updateEnv = (config: any) => {
    setIsloading(true);
    if (config !== null) {
      let tmp_tabs: any[] = [];
      setProjectName(config.project);
      setAuthor(config.author);
      if (config.login?.user) {
        tmp_tabs.push({
          label: (
            <div style={{ width: 100, textAlign: 'right' }}>
              {t('auth:username')}
            </div>
          ),
          id: 'user',
          content: (
            <User
              username={username}
              password={password}
              setUsername={setUsername}
              setPassword={setPassword}
            />
          ),
          disabled: config.login?.user?.disabled || false,
        });
      }
      if (config.login?.sns) {
        tmp_tabs.push({
          label: (
            <div style={{ paddingLeft: 15, width: 120, textAlign: 'center' }}>
              {t('auth:sns')}
            </div>
          ),
          id: 'sns',
          disabled: config.login.sns.disabled || false,
          content: (
            <SNS
              username={username}
              password={password}
              setUsername={setUsername}
              setPassword={setPassword}
            />
          ),
        });
      }
      if (config.login?.oidc && config.login.oidc.providers.length > 0) {
        // const tmp_login_params = new Map<string, any>();
        config.login.oidc.providers.forEach((item: any) => {
          let description = '';
          switch (item.name) {
            case 'keycloak':
              description = t('auth:keycloakDesc');
              break;
            case 'authing':
              description = t('auth:authingDesc');
              break;
            default:
              description = t('auth:cognitoDesc');
              break;
          }
          oidcOptions.push({
            label: item.label,
            iconUrl: `imgs/${item.name}.png`,
            value: item.name,
            clientId: item.clientId,
            clientSecret: item.clientSecret,
            redirectUri: item.redirectUri,
            disabled: item.disabled || false,
            tags: [description],
          });
          // tmp_login_params.set(item.name, item)
        });
        if (!builtInConfig?.oidcRegion.startsWith('cn-')) {
          oidcOptions.push({
            label: 'Cognito',
            iconUrl: 'imgs/cognito.png',
            value: 'cognito',
            clientId: builtInConfig?.oidcClientId,
            // clientSecret: item.clientSecret,
            redirectUri: builtInConfig?.oidcRedirectUrl,
            tags: [t('auth:cognitoDesc')],
          });
        }

        setOidcList(oidcOptions);

        tmp_tabs.push({
          label: (
            <div style={{ width: 120, textAlign: 'center' }}>
              {t('auth:oidc')}
            </div>
          ),
          id: 'oidc',
          disabled: config.login?.oidc.disabled || false,
          content: (
            <OIDC
              provider={selectedProvider || oidcOptions[0]}
              username={username}
              password={password}
              oidcOptions={oidcOptions}
              setSelectedProviderName={setSelectedProviderName}
              setProvider={setSelectedProvider}
              setUsername={setUsername}
              setPassword={setPassword}
              setError={setError}
            />
          ),
        });
      }
      setTabs(tmp_tabs);
      setIsloading(false);
    }
  };

  const changeLanguage = () => {
    if (lang === EN_LANG) {
      setLang(ZH_LANG);
      i18n.changeLanguage(ZH_LANG);
    } else {
      setLang(EN_LANG);
      i18n.changeLanguage(EN_LANG);
    }
  };

  const forgetPwd = () => {
    navigate(ROUTES.FindPWD);
  };

  const toRegister = () => {
    navigate(ROUTES.Register);
  };

  const loginSystem = () => {
    let currentProvider = selectedProvider;
    const ver = version;
    setError('');
    setLogging(true);
    if (activeTabId === LOGIN_TYPE.OIDC && currentProvider == null) {
      setSelectedProvider(oidcList[0]);
      currentProvider = oidcList[0];
    }
    if (username == null || username === '') {
      setError(t('auth:error.username').toString());
      setVersion(ver + 1);
      setLogging(false);
      return;
    }
    if (password == null || password === '') {
      setError(t('auth:error.username').toString());
      setVersion(ver + 1);
      setLogging(false);
      return;
    }
    oidcLogin(currentProvider);
  };

  // const ssoLogin =async (ssoType: string) => {
  //   setIsloading(true)
  //   switch(ssoType){
  //     case "midway":
  //       await midway()
  //       break;
  //     default:
  //       break;
  //   }
  // }

  // const midway = async () =>{
  //   const midwayConfig = config?.login.sso.midway;
  //   const app_url = localStorage.getItem(APP_URL)
  //   let signInProd: null | string = null
  //   let signOutProd: null | string = null
  //   if(app_url){
  //     signInProd = `https://${app_url}/login`;
  //     signOutProd = `https://${app_url}`
  //   }
  //   try {
  //   Amplify.configure({
  //     Auth: {
  //       Cognito: {
  //         userPoolId: midwayConfig?.user_pool_id,
  //         userPoolClientId: midwayConfig?.user_pool_client_id,
  //         identityPoolId: "",
  //         allowGuestAccess: true,
  //         loginWith: {
  //           oauth: {
  //             domain: midwayConfig?.auth.domain,
  //             scopes: ['aws.cognito.signin.user.admin', 'email', 'openid', 'profile'],
  //             redirectSignIn: [midwayConfig?.auth.redirect_signin_local, signInProd],
  //             redirectSignOut: [midwayConfig?.auth.redirect_signout_local, signOutProd],
  //             responseType: "code",
  //           }
  //           }
  //         }
  //       }
  //     }
  //   )
  //   await signInWithRedirect({
  //       provider:{
  //         custom: midwayConfig?.provider
  //       }
  //       })
  //   } catch (error){
  //     if ((error as { name: string }).name === 'UserAlreadyAuthenticatedException') {
  //       console.warn('User already signed in. Fetching user info...');
  //       await processForUserAlreadySignin(navigate)
  //     } else {
  //       console.error('Error during sign in:', error);
  //     }
  //   }
  // }
  const loginWithCognito = async () => {
    let res = '';
    try {
      Amplify.configure({
        Auth: {
          Cognito: {
            userPoolId: builtInConfig?.oidcPoolId || '',
            userPoolClientId: builtInConfig?.oidcClientId || '',
          },
        },
      });
      const user = await signIn({ username, password });
      console.log(`user is ${user}`);
    } catch (error: any) {
      // if (error.name == 'NotAuthorizedException') {
      res = error.message;
      // } else {
      //   setError(t('auth:unknownError').toString());
      // }
      // return false
    }
    return res;
  };

  const loginWithAuthing = async (currentProvider: any, provider: string) => {
    let res = '';
    try {
      const response = await fetchData({
        url: '/auth/login',
        method: 'post',
        data: {
          redirect_uri: currentProvider.redirectUri,
          client_id: currentProvider.clientId,
          provider,
          username,
          password,
        },
      });
      localStorage.setItem(
        `oidc.${currentProvider.label}.${currentProvider.clientId}`,
        JSON.stringify(response.body),
      );
    } catch (error) {
      if (error instanceof AxiosError) {
        let detail = error.response?.data.detail;
        if (typeof detail === 'string') detail = JSON.parse(detail);
        if (detail) {
          res = detail.error_description;
        }
      } else {
        res = t('auth:unknownError').toString();
      }
      // return
    }
    return res;
  };

  // let userInfo: any= {}
  const oidcLogin = async (currentProvider: any) => {
    let returnMsg = '';
    const provider = currentProvider.label.toLowerCase();
    if (provider === 'cognito') {
      returnMsg = await loginWithCognito();
    } else {
      returnMsg = await loginWithAuthing(currentProvider, provider);
    }
    if (returnMsg) {
      setError(returnMsg);
      setLogging(false);
      return;
    }

    localStorage.setItem(
      OIDC_STORAGE,
      JSON.stringify({
        provider: currentProvider.label,
        client_id: currentProvider.clientId,
        redirect_uri: currentProvider.redirectUri,
      }),
    );
    navigate(ROUTES.Home);
    if (isLoading) {
      return <Spinner />;
    }
  };

  return isLoading ? (
    <div style={{ paddingTop: '20%', paddingLeft: '50%' }}>
      <Spinner size="large" />
    </div>
  ) : (
    <div className="login-div">
      <SpaceBetween direction="vertical" size="m">
        <div className="container">
          <div className="banner">{projectName}</div>
          <div className="sub-title">
            {t('auth:support-prefix')} {author} {t('auth:support-postfix')}{' '}
            <Link variant="info" onFollow={() => changeLanguage()}>
              {t('auth:changeLang')}
            </Link>
          </div>
          <div className="tab" style={{ paddingLeft: '10%' }}>
            <Tabs
              onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
              activeTabId={activeTabId}
              tabs={tabs}
            />
            <div className="bottom-setting">
              <Grid gridDefinition={[{ colspan: 4 }, { colspan: 8 }]}>
                <div>
                  <Checkbox
                    onChange={({ detail }) => setKeep(detail.checked)}
                    checked={keep}
                  >
                    <span className="keep">{t('auth:keepLogin')}</span>
                  </Checkbox>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <Link onFollow={forgetPwd}>{t('auth:forgetPWD')}</Link>
                  &nbsp;&nbsp;&nbsp;
                  <Link onFollow={toRegister}>{t('auth:register')}</Link>
                </div>
              </Grid>
            </div>
            <div className="button-group">
              <Button
                variant="primary"
                className="login"
                loading={logging}
                onClick={loginSystem}
              >
                {t('auth:login')}
              </Button>
              <Grid
                gridDefinition={[
                  { colspan: 5 },
                  { colspan: 2 },
                  { colspan: 5 },
                ]}
              >
                <div
                  style={{ marginTop: 20, borderBottom: '1px solid #ccc' }}
                ></div>
                <div
                  style={{ textAlign: 'center', paddingTop: 8, color: '#ccc' }}
                >
                  {t('auth:or')}
                </div>
                <div
                  style={{ marginTop: 20, borderBottom: '1px solid #ccc' }}
                ></div>
              </Grid>
              <div style={{ marginTop: 12 }}>
                <Button
                  className="login"
                  onClick={() => {
                    console.log('SSO');
                  }}
                  disabled
                >
                  {t('auth:sso')}
                </Button>
              </div>
              <div
                style={{
                  marginTop: 30,
                  textAlign: 'right',
                  color: 'red',
                  fontWeight: 800,
                  height: 16,
                }}
              >
                {error}
              </div>
              {/* <div style={{height:20, marginTop: 16, color:"#d93a7f7a", fontWeight:"bold", fontSize:12}}>{(error!==""&& error!==null)?(<><span style={{fontWeight: 800}}>·</span>&nbsp;{error}</>):""}</div> */}
            </div>
            <div style={{ display: 'none' }}>{selectedProviderName}</div>
          </div>
        </div>
      </SpaceBetween>
    </div>
  );
};

export default Login;

// const processForUserAlreadySignin = async(navigate: any) => {
//   try {
//     const currentSession = await fetchAuthSession();
//     const currentUser = await fetchUserAttributes();
//     localStorage.setItem(OIDC_STORAGE, "midway");
//     localStorage.setItem(USER, currentUser.email?.split('@')[0] || currentUser.username || currentUser.name || "");
//     localStorage.setItem(TOKEN, JSON.stringify({ access_token: currentSession.tokens?.accessToken.toString(), id_token: currentSession.tokens?.idToken?.toString() }));
//     navigate(ROUTES.Home);
//   } catch (error) {
//     if ((error as { name: string }).name === 'NotAuthorizedException') {
//       await signOut({ global: true });
//       return null;
//     } else {
//       console.error('Failed to fetch current user:', error);
//     }
//   }
// }
