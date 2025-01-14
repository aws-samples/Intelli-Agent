import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import '@cloudscape-design/global-styles/index.css';
import './index.scss';
import './i18n';
import ConfigProvider from './context/config-provider.tsx';
import { Provider } from 'react-redux';
import { store } from './app/store.ts';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider>
      <Provider store={store}>
        <App />
      </Provider>
    </ConfigProvider>
  </React.StrictMode>,
);
