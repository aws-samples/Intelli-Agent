// import React from 'react';
// import ReactDOM from 'react-dom/client';
// import App from './App.tsx';
// import '@cloudscape-design/global-styles/index.css';
// import './index.scss';
// import './i18n';
// import ConfigProvider from './context/config-provider.tsx';
// import { Provider } from 'react-redux';
// import { store } from './app/store.ts';

// ReactDOM.createRoot(document.getElementById('root')!).render(
//   <React.StrictMode>
//     <ConfigProvider>
//       <Provider store={store}>
//         <App />
//       </Provider>
//     </ConfigProvider>
//   </React.StrictMode>,
// );

import ReactDOM from 'react-dom/client';
import App from './App';
import '@cloudscape-design/global-styles/index.css';
import './i18n';
import reportWebVitals from './reportWebVitals';


const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
<App />
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();

