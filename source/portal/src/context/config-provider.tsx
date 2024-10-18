import React, { useState, useEffect } from 'react';
import ConfigContext, { Config } from './config-context';
import { Spinner } from '@cloudscape-design/components';
import { alertMsg } from 'src/utils/utils';
interface ConfigProviderProps {
  children: React.ReactNode;
}

const ConfigProvider: React.FC<ConfigProviderProps> = ({ children }) => {
  const [config, setConfig] = useState<Config | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch('/aws-exports.json');
        const data: Config = await response.json();
        setConfig(data);
      } catch (error) {
        alertMsg('Please check aws-exports.json file', 'error');
        console.error('Failed to fetch config:', error);
      }
    };
    fetchConfig();
  }, []);

  if (!config) {
    return (
      <div className="page-loading">
        <Spinner />
      </div>
    );
  }

  // const updateOIDC = (newOIDC: string) => {
  //   setConfig((prevInfo: any) => ({
  //     ...prevInfo,
  //     oidc: newOIDC
  //   }));
  // };

  return (
    <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>
  );
};

export default ConfigProvider;
