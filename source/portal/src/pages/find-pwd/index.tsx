import { Button, Checkbox, FormField, Grid, Input, Link, Select } from '@cloudscape-design/components';
import { FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import yaml from 'yaml';
import './style.scss';
import { EN_LANG, ROUTES, ZH_LANG, ZH_LANGUAGE_LIST } from 'src/utils/const';
import { useTranslation } from 'react-i18next';

const FindPWD: FC = () => {
  const navigate = useNavigate();
  const [error, setError] = useState(null as any);
  const [projectName, setProjectname] = useState("" as string);
  const [loginType, setLoginType] = useState([] as any[]);
  const [selectedLoginType, setSelectedLoginType] = useState("oidc" as string);
  const [thirdLogin, setThirdLogin] = useState([] as any[]);
  const [author, setAuthor] =useState("" as string)
  const [username, setUsername] =useState("" as string)
  const [oidcProvider, setOidcProvider] =useState(null as any)
  const [oidcOptions, setOidcOptions] = useState([] as any[]);
  const { t, i18n } = useTranslation();
  const [lang, setLang]= useState('')
  
  useEffect(()=>{
    let tmp_login_type: any[] =[]
    let tmp_third_login: any[] =[]
    if (ZH_LANGUAGE_LIST.includes(i18n.language)) {
      setLang(ZH_LANG)
      i18n.changeLanguage(ZH_LANG);
    } else {
      setLang(EN_LANG)
      i18n.changeLanguage(EN_LANG);
    }
    const loadConfig = async ()=> {
      let response = await fetch('/config.yaml')
      let data = await response.text()
      return yaml.parse(data);
    }
    loadConfig().then(configData =>{
      setProjectname(configData.project)
      setAuthor(configData.author)
      if(configData.login.user){
        tmp_login_type.push({
          label: t('auth:username'),
          value: configData.login.user.value,
          disabled: configData.login.user.disabled || false
        })
      }
      if(configData.login.sns){
        tmp_login_type.push({
          label: t('auth:sns'),
          value: configData.login.sns.value,
          disabled: configData.login.sns.disabled || false
        })
      }
      if(configData.login.oidc && configData.login.oidc.providers.length > 0){
        const oidcOptions:any[] =[]
        configData.login.oidc.providers.forEach((item:any)=>{
          oidcOptions.push({
            label: item.label,
            iconUrl:`../../imgs/${item.name}.png`,
            value: item.label,
            tags: [genOIDCDesc(item.name)]
          })
        })
        tmp_login_type.push({
          label: t('auth:oidc'),
          value: configData.login.oidc.value,
          disabled: configData.login.oidc.disabled || false
        })
        setOidcOptions(oidcOptions)
      }
      if(configData.login.third && configData.login.third.length > 0){
        tmp_third_login = configData.login.third
        setThirdLogin(tmp_third_login)
      }
      setLoginType(tmp_login_type)
    })
  })

  const genOIDCDesc=(name: string)=>{
    let description = ""
    switch(name){
      case "keycloak":
        description = t('auth:keycloakDesc');
        break;
      case "authing":
        description = t('auth:authingDesc');
        break;
      default:
        description = t('auth:cognitoDesc');
        break;
    }
    return description
  }
  
  const changeLoginType = (checked:boolean,loginType: string)=>{
    if(checked){ 
      setSelectedLoginType(loginType)
    } else{
      setSelectedLoginType("")
    }
    
  }

  const changeLanguage = () => {
    if(lang===EN_LANG){
      setLang(ZH_LANG)
      i18n.changeLanguage(ZH_LANG);
    } else {
      setLang(EN_LANG)
      i18n.changeLanguage(EN_LANG);
    } 
  };

  const toLogin =()=>{
    navigate(ROUTES.Login)
  }

  const toRegister =()=>{
    navigate(ROUTES.Register)
  }
  
  const sendEmail=()=> {
    setError(t('auth:waiting'))
  }

  return (
    <div className="pwd-div">
      <div className='container'>
        <div className='banner'>{projectName}</div>
        <div className='sub-title'>{t('auth:support-prefix')} {author} {t('auth:support-postfix')} <Link variant="info" onFollow={()=>changeLanguage()}>{t('auth:changeLang')}</Link></div>
        <div className='tab' style={{paddingLeft:'10%'}}>
          <div style={{height:270,width:'90%'}}>
          <div style={{color:"#000000a6",fontSize:18, fontWeight:800, marginBottom:20}}>{t('auth:findPWD.title')}</div>
          <div style={{width:'100%'}}>
            <Grid gridDefinition={[{colspan:4},{colspan:4},{colspan:4}]}>
              {loginType.map(item=>(<div>
                <Checkbox
                  disabled={item.disabled}
                  checked={selectedLoginType === item.value}
                  onChange={({ detail }) => {
                      changeLoginType(detail.checked,item.value);
                  }}
                >
                  {item.label}
                </Checkbox>
              </div>))}
            </Grid>
            {(selectedLoginType==='username')?(
              <div style={{marginTop:35}}>
                <FormField
                  description="Please enter a valid email address. If it exists and is associated with an existing user, we will send a password reset email to this address..."
                  label="Email"
                >
                  <Input
                    value={username}
                    placeholder='eg: Peter'
                    onChange={event =>
                      setUsername(event.detail.value)
                    }
                  />
                </FormField>
              </div>):((selectedLoginType==='oidc')?(<div style={{marginTop:15}}>
                <FormField
                  description={t('auth:findPWD.oidcDesc')}
                  label={t('auth:findPWD.oidc')}
                >
                  <div className='item'>
                    <Select
                      placeholder={t('auth:findPWD.oidcPlaceholder').toString()}
                      selectedOption={oidcProvider||oidcOptions[0]}
                      onChange={({ detail }:{detail: any}) =>
                        setOidcProvider(detail.selectedOption)
                      }
                      options={oidcOptions}
                    />
                  </div>
                </FormField>
    <FormField
      description={t('auth:findPWD.usernameDesc')}
      label={t('auth:findPWD.username')}
    >
      <Input
        value={username}
        placeholder={t('auth:findPWD.usernamePlaceHolder').toString()}
        onChange={event =>
          setUsername(event.detail.value)
        }
      />
    </FormField>
              </div>):(<>
              </>))}
          </div>
        </div>
        <div className='button-group'>
          <Button variant="primary" className='send-email' onClick={()=>{sendEmail()}}>{t('auth:findPWD.send')}</Button>
        </div>
        <div style={{color: 'rgb(128, 128, 128)', fontSize: 14,marginTop: 30, width:'90%'}}>
          {(thirdLogin && thirdLogin.length>0)?(
          <Grid gridDefinition={[{colspan:4},{colspan:8}]}>
            <div style={{paddingTop:15, textAlign:'right'}}>
              <span style={{color: 'rgb(128, 128, 128)'}}>{t('auth:needAccount')}</span>
              <Link onFollow={toRegister}>{t('auth:register')}</Link>
              <span style={{color: 'rgb(128, 128, 128)'}}> {t('auth:or')} </span>
              <Link onFollow={toLogin}>{t('auth:login')}</Link>
            </div>
          </Grid>):(
          <Grid gridDefinition={[{colspan:12}]}>
            <div style={{paddingTop:5, textAlign:'right'}}>
              <span style={{color: 'rgb(128, 128, 128)'}}>{t('auth:needAccount')}</span>
              <Link onFollow={toRegister}>{t('auth:register')}</Link>
              <span style={{color: 'rgb(128, 128, 128)'}}> {t('auth:or')} </span>
              <Link onFollow={toLogin}>{t('auth:login')}</Link>
            </div>
          </Grid>)}
          <div style={{marginTop:10,textAlign:'right',color:'red',fontWeight:800,height:16}}>{error}</div>
        </div>
      </div>   
    </div>
  </div>
  );
};

export default FindPWD;
