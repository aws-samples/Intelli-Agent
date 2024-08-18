import { AuthFlowType, CognitoIdentityProviderClient, InitiateAuthCommand } from '@aws-sdk/client-cognito-identity-provider';
import ConfigContext from 'src/context/config-context';
import { Button, Checkbox, Grid, Link, SpaceBetween, Spinner, Tabs } from '@cloudscape-design/components';
import { FC, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import yaml from 'yaml';
import OIDC from './component/oidc';
import SNS from './component/sns';
import User from './component/user';
import './style.scss';
import axios, { AxiosError } from 'axios';
import { AUTHING, LOGIN_TYPE, PROVIDER, ROUTES, TOKEN, USER } from 'src/utils/const';
import useAxiosRequest from 'src/hooks/useAxiosRequest';

const Login: FC = () => {
  const [activeTabId, setActiveTabId] = useState(LOGIN_TYPE.OIDC);
  const [logging, setLogging] = useState(false as boolean);
  const [username, setUsername] = useState(null as any);
  const [password, setPassword] = useState(null as any);
  const [keep, setKeep] = useState(false);
  const navigate = useNavigate();
  const [error, setError] = useState("" as string);
  const [config, setConfig]=useState(null as any);
  const [selectedProvider, setSelectedProvider] = useState(null as any);
  const [selectedProviderName, setSelectedProviderName] = useState(null as any);
  const [selectedThird, setSelectedThird]  = useState("" as string);
  const [tabs, setTabs] = useState([] as any[]);
  const [thirdLogin, setThirdLogin] = useState([] as any[]);
  const [projectName, setProjectName] = useState("" as string)
  const [author, setAuthor] = useState("" as string)
  const [version, setVersion] = useState(0)
  const [loginParams, setLoginParams] = useState(null as any);
  const [isLoading, setIsloading] = useState(true)
  const fetchData = useAxiosRequest();
  const configContext = useContext(ConfigContext);

  useEffect(()=>{
    // const currentRegion = getCurrentRegion()
    // const currentClientId = getCloudFormationOutput("", "")
    const loadConfig = async ()=> {
      let response = await fetch('/config.yaml')
      let data = await response.text()
      return yaml.parse(data);
    }
    loadConfig().then(configData =>{
      setConfig(configData)
      setIsloading(false)
    })
    setError("")
    // setRegion(currentRegion)
  },[])

  useEffect(()=>{
      if(config!==null){
      let tmp_tabs: any[] =[]
      let tmp_third_login: any[] =[]
      setProjectName(config.project)
      setAuthor(config.author)
      if(config.login.user){
        tmp_tabs.push({
          label: <div style={{width:100, textAlign: 'right'}}>{config.login.user.label}</div>,
          id: "user",
          content: (<User 
                      username={username}
                      password={password}
                      setUsername={setUsername}
                      setPassword={setPassword}
                    />),
          disabled: config.login.user.disabled || false
        })
      }
      if(config.login.sns){
        tmp_tabs.push({
          label: <div style={{paddingLeft:20,width:120, textAlign: 'center'}}>{config.login.sns.label}</div>,
          id: "sns",
          disabled: config.login.sns.disabled || false,
          content: (<SNS 
                      username={username}
                      password={password}
                      setUsername={setUsername}
                      setPassword={setPassword}
                    />)
        })
      }
      if(config.login.oidc && config.login.oidc.providers.length > 0){
        const tmp_login_params = new Map<string, any>();
        const oidcOptions:any[] =[]
        config.login.oidc.providers.forEach((item:any)=>{
          oidcOptions.push({
            label: item.name,
            iconUrl:`../../imgs/${item.iconUrl}.png`,
            value: item.name,
            clientId: item.clientId,
            clientSecret: item.clientSecret,
            redirectUri: item.redirectUri,
            disabled: item.disabled || false,
            tags: [item.description]
            
          })
          tmp_login_params.set(item.name, item)
        })
        tmp_tabs.push({
          label: <div style={{width:120, textAlign: 'center'}}>{config.login.oidc.label}</div>,
          id: "oidc",
          disabled: config.login.oidc.disabled || false,
          content: (<OIDC
            provider= {selectedProvider}
            username={username}
            password={password}
            oidcOptions={oidcOptions}
            setSelectedProviderName={setSelectedProviderName}
            setProvider={setSelectedProvider}
            setUsername={setUsername}
            setPassword={setPassword}
          />)
        })
        setLoginParams(tmp_login_params)
      }
      if(config.login.third && config.login.third.length > 0){
        tmp_third_login = config.login.third
        setThirdLogin(tmp_third_login)
      }
      setTabs(tmp_tabs)}
  },[config, selectedProvider, username, password])
   
  const forgetPwd =()=>{
    navigate(ROUTES.FindPWD)
  }

  const handleMouseEnter =(target: string)=>{
    setSelectedThird(target)
  }

  const handleMouseLeave =(target: string)=>{
    setSelectedThird("")
  }

  const toRegister =()=>{
    navigate(ROUTES.Register)
  }

  const loginSystem = () => {
    const ver = version
    setLogging(true)
    if(activeTabId === LOGIN_TYPE.OIDC && selectedProvider == null){
      setError("provideId is required")
      setVersion(ver + 1)
      setLogging(false)
      return;
    }
    if(username == null || username == ''){
      setError("username is required")
      setVersion(ver + 1)
      setLogging(false)
      return;
    }
    if(password == null || password == ''){
      setError("password is required")
      setVersion(ver + 1)
      setLogging(false)
      return;
    }

    switch(selectedProvider.value){
      case "Cognito":
        cognitoLogin();
        break;
      default:
        oidcLogin(selectedProvider.value.toLowerCase())
        break;
    }
  }
    const cognitoLogin = async()=>{
  try {
    // "oidcIssuer":"https://cognito-idp.us-east-1.amazonaws.com/us-east-1_kebZf6bDh"
    // const oidcIssuer = configContext?.currentOidc.oidcIssuer
    const authResponse = await initiateAuth(configContext?.currentOidc.clientId, configContext?.currentOidc.clientId.region, username, password);
      if(authResponse.ChallengeName==="NEW_PASSWORD_REQUIRED"){
        navigate(ROUTES.ChangePWD, { 
          state: {
            session: authResponse.Session,
            reason:"First Login",
            username,
            loginType: activeTabId,
            provider: selectedProviderName,
            author,
            thirdLogin,
            region: selectedProvider.region,
            clientId: selectedProvider.clientId
          }
        });
      }
    if (authResponse.AuthenticationResult) {
      // localStorage.setItem("loginType", activeTabId || '');
      localStorage.setItem(PROVIDER, "cognito");
      localStorage.setItem(TOKEN, JSON.stringify(authResponse.AuthenticationResult));
      localStorage.setItem("userName", username || '');
      // localStorage.setItem("accessToken", authResponse.AuthenticationResult.AccessToken || '');
      // localStorage.setItem("refreshToken", authResponse.AuthenticationResult.RefreshToken || '');
      localStorage.setItem("session", authResponse.Session || '');
      navigate(ROUTES.ChatBot)
    }
  } catch (error) {
    if(error instanceof Error) {
      setError(error.message)
    } else {
      setError("Unknown error, please contact the administrator.")
    }
    setLogging(false)
    return
  }
}

const oidcLogin = async(oidc: string)=>{
  let response: any
  let userInfo: any
  let payload: any
  let redirectUri: string
  const headers = {'Content-Type': 'application/x-www-form-urlencoded'}
  if(oidc==='authing'){
    redirectUri = AUTHING.REDIRECT_URI
    payload = {
      "client_id": AUTHING.CLIENT_ID,
      "client_secret": AUTHING.CLIENT_SECRET,
      "grant_type": "password",
      "username": username,
      "password": password
    }
    try{
      response = await axios({
        method: "post",
        url: `${redirectUri}/oidc/token`,
        data: payload,
        headers,
      });
    } catch (error){
      if(error instanceof AxiosError) {
        setError(JSON.parse(error.response?.data.detail).error_description)
      } else {
        setError("Unknown error, please contact the administrator.")
      }
      setLogging(false)
      return
    }
    userInfo = await axios.get(
      `${redirectUri}/oidc/me`,
      {
        headers: {
          'Authorization': `Bearer ${response.data.access_token}`,
        }
      }
    );
  }
  localStorage.setItem(PROVIDER, oidc)
  localStorage.setItem(TOKEN, JSON.stringify(response.data));
  localStorage.setItem("userName", username || '');
  // localStorage.setItem(USER, JSON.stringify(userInfo.data));
  navigate(ROUTES.ChatBot)
}

  if(isLoading){
    return (
      <Spinner/>
    )
  }
  
  return (
    <div className="login-div">   
      <div className='container'>
        <div className='banner'>{projectName}</div>
        <div className='sub-title'>Supported by {author}</div>
        <div className='tab' style={{paddingLeft:'10%'}}>
        <Tabs
          onChange={({ detail }) =>
            setActiveTabId(detail.activeTabId)
          }
          activeTabId={activeTabId}
          tabs={tabs}
        />
        <div className='bottom-setting'>
    <Grid
      gridDefinition={[{ colspan: 4 },{ colspan: 8 }]}
    >
      <div>
      <Checkbox
      onChange={({ detail }) =>
        setKeep(detail.checked)
      }
      checked={keep}
    >
      <span className='keep'>Keep me logged in</span>
    </Checkbox>
      </div>
      <div style={{textAlign:"right"}}>
      <Link onFollow={forgetPwd} >
      Forgot Password
    </Link>
      </div>
    </Grid>
    </div>
    <div className='bottom-button'>
    <Button variant="primary" className='login-buttom' loading={logging} onClick={loginSystem}>Log in</Button>
    </div>
    <div style={{display:'none'}}>{selectedProviderName}</div>
    <div style={{color: 'rgb(128, 128, 128)', fontSize: 14,marginTop: 30, width:'90%'}}>
      {(thirdLogin && thirdLogin.length>0)?(<Grid gridDefinition={[{colspan:6},{colspan:6}]}>
        <SpaceBetween direction='horizontal' size='s'>
          {thirdLogin.map(item=>{
             return (<div key={item.type} onMouseEnter={()=>handleMouseEnter(item.type)} onMouseLeave={()=>handleMouseLeave(item.type)}>
             <img src={selectedThird===item.type? `../imgs/${item.iconUrlSelected}.png`:`../imgs/${item.iconUrl}.png`} alt="" style={item.iconStyle}/>
           </div>)
          })}
        </SpaceBetween>
        <div style={{paddingTop:15, textAlign:'right'}}>
          <span style={{color: 'rgb(128, 128, 128)'}}>Don't have an account? </span>
          <Link onFollow={toRegister}>Register</Link>
        </div>
      </Grid>):(<Grid gridDefinition={[{colspan:12}]}>
        <div style={{paddingTop:5, textAlign:'center'}}>
          <span style={{color: 'rgb(128, 128, 128)'}}>Don't have an account? </span>
          <Link onFollow={toRegister}>Register</Link>
        </div>
        <div style={{display:"none"}}>{version}</div>
      </Grid>)}
      <div style={{marginTop:10,textAlign:'right',color:'red',fontWeight:800,height:16}}>{error}</div>
    </div>
    </div>
      
      </div>
    </div>
  );
};

export default Login;
const initiateAuth= async(clientId: string, region: string, username:string, password:string) => {
  const params = {
      AuthFlow: AuthFlowType.USER_PASSWORD_AUTH,
      ClientId: clientId,
      AuthParameters: {
        USERNAME: username,
        PASSWORD: password,
      }
  }
  const client = new CognitoIdentityProviderClient({
      region,
  });
  const command = new InitiateAuthCommand(params);
  return await client.send(command);
};
