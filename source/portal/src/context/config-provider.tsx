import React, { useState, useEffect } from 'react';
import ConfigContext, { Config } from './config-context';
import { Spinner } from '@cloudscape-design/components';
import { alertMsg } from 'src/utils/utils';
interface ConfigProviderProps {
  children: React.ReactNode;
}

const ConfigProvider: React.FC<ConfigProviderProps> = ({ children }) => {
  const [config, setConfig] = useState<Config | null>(null as any);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch('/aws-exports.json');
        const res = await response.json();
      //  console.log(`/aws-exports.json is ${JSON.stringify(res)}`)
        
        setConfig((prev)=> ({
          ...(prev || {
            websocket: '',
            apiUrl: '',
            docsS3Bucket: '',
            workspaceId: '',
            builtInCognito: {
              oidcIssuer: '',
              oidcClientId: '',
              oidcLogoutUrl: '',
              oidcRedirectUrl: '',
              region: ''
            },
            currentUser: {},
            currentOidc: {},
            updateOIDC: () => {}
          }),
          websocket:res.websocket,
          apiUrl: res.apiUrl,
          builtInCognito: {
            ...({
              oidcIssuer: res.oidcIssuer,
              oidcClientId: res.oidcClientId,
              oidcLogoutUrl: res.oidcLogoutUrl,
              oidcRedirectUrl: res.oidcRedirectUrl,
              region: res.region
            }),
          }
        }));
      } catch (error) {
        alertMsg('Please check aws-exports.json file', 'error');
        console.error('Failed to fetch config:', error);
      }
    };
    fetchConfig();
  }, []);

  const updateOIDC=(newOIDC: string)=>{
     console.log("updateOIDC")
    //  console.log(newOIDC)
    const tmp_config = config
    if(tmp_config){
      tmp_config.currentOidc = newOIDC
    }
    setConfig(tmp_config)
  }

  if (!config) {
    return (
      <div className="page-loading">
        <Spinner />
      </div>
    );
  }

  return (
    <ConfigContext.Provider value={{...config, updateOIDC}}>{children}</ConfigContext.Provider>
  );
};

export default ConfigProvider;
