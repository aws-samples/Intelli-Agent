import React from 'react';
export interface Config {
  websocket: string;
}
const ConfigContext = React.createContext<Config | null>(null);
export default ConfigContext;
