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
import { signIn, fetchAuthSession } from '@aws-amplify/auth';



const Login: FC = () => {
  const [activeTabId, setActiveTabId] = useState(LOGIN_TYPE.OIDC);
  const [logging, setLogging] = useState(false as boolean);
  const [username, setUsername] = useState(null as any);
  const [password, setPassword] = useState(null as any);
  const [keep, setKeep] = useState(false);
  const navigate = useNavigate();
  // const { i18n } = useTranslation();
  const { t, i18n } = useTranslation();
  const fetchData = useAxiosAuthRequest();
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
      setError(t('auth:error.password').toString());
      setVersion(ver + 1);
      setLogging(false);
      return;
    }
    oidcLogin(currentProvider);
  };

  function removeKeysWithPrefix(prefix: string) {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i);
      if (key && key.startsWith(prefix)) {
        localStorage.removeItem(key);
      }
    }
  }

  const loginWithCognito = async (currentProvider: any) => {
    let res = '';
    try {
      Amplify.configure({
        Auth: {
          Cognito: {
            userPoolId: builtInConfig?.oidcPoolId || '',
            userPoolClientId: builtInConfig?.oidcClientId || ''
          },
        },
      });
      const user = await signIn({ 
        username, 
        password
      });
      console.log(`user is ${user}`);
      const session = await fetchAuthSession();
      localStorage.setItem(
        `oidc.${currentProvider.value}.${currentProvider.clientId}`,
        JSON.stringify({
          accessToken: session.tokens?.accessToken.toString(),
          idToken: session.tokens?.idToken?.toString(),
          username: session.tokens?.signInDetails?.loginId
        }),
      );
      removeKeysWithPrefix("CognitoIdentityServiceProvider")
      // localStorage.removeItem("CognitoIdentityServiceProvider.aded2oqehr9748gg29ds24ic5.LastAuthUser")
      console.log(session)
    } catch (error: any) {
      if(error.name === 'NotAuthorizedException') {
      res = t('auth:incorrectPWD');
    } else if(error.name === 'UserNotFoundException') {
      res = t('auth:userNotExists');
    } else {
      res = t('auth:unknownError');
    }

    }
    return res;
  };

  const loginWithAuthing = async (currentProvider: any, provider: string) => {
    let res = '';
    try {
      const response = await fetchData({
        url: 'auth/login',
        method: 'post',
        data: {
          redirect_uri: currentProvider.redirectUri,
          client_id: currentProvider.clientId,
          provider,
          username,
          password,
          lang: i18n.language === 'zh'? "zh-CN" : "en-US"
        },
      });
      if(response.body.error) {
        res = response.body.error_description
        return res;
      }
      localStorage.setItem(
        `oidc.${currentProvider.value}.${currentProvider.clientId}`,
        JSON.stringify(response.body),
      );
    } catch (error) {
      if (error instanceof AxiosError) {
        let detail = error.response?.data.detail;
        if (typeof detail === 'string') detail = JSON.parse(detail);
        if (detail) {
          res = detail.error_description;
        } else {
          res = t('auth:unknownError').toString();
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
    const provider = currentProvider.value;
    if (provider === 'cognito') {
      returnMsg = await loginWithCognito(currentProvider);
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
        username,
        provider: currentProvider.value,
        clientId: currentProvider.clientId,
        redirectUri: currentProvider.redirectUri,
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
