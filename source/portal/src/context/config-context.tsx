import React from 'react';
export interface Config {
  websocket: string;
  apiUrl: string;
  docsS3Bucket: string;
  workspaceId: string;
  builtInCognito: {
    oidcIssuer: string;
    oidcClientId: string;
    oidcLogoutUrl: string;
    oidcRedirectUrl: string;
    region: string;
  }
  currentUser?: any,
  currentOidc?: any,
  updateOIDC: (newOIDC: string)=>void
}
const ConfigContext = React.createContext<Config | null>(null);
export default ConfigContext;
