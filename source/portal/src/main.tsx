import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import '@cloudscape-design/global-styles/index.css';
import './index.scss';
import './i18n';
import ConfigProvider from './context/config-provider.tsx';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
