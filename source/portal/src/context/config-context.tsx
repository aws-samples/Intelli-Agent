import React from 'react';
export interface Config {
  websocket: string;
  apiUrl: string;
  docsS3Bucket: string;
  workspaceId: string;
  oidcIssuer: string;
  oidcClientId: string;
  oidcLogoutUrl: string;
  oidcRedirectUrl: string;
  // apiKey: string;
}
const ConfigContext = React.createContext<Config | null>(null);
export default ConfigContext;
