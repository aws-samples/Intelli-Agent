// import { useContext } from 'react';
// import ConfigContext from './context/config-context';
// import { AuthProvider } from 'react-oidc-context';
// import AppRouter from './Router';
// import { WebStorageStateStore } from 'oidc-client-ts';

// function App() {
//   const config = useContext(ConfigContext);
//   const oidcConfig = {
//     userStore: new WebStorageStateStore({ store: window.localStorage }),
//     scope: 'openid email profile',
//     automaticSilentRenew: true,
//     authority: config?.oidcIssuer,
//     client_id: config?.oidcClientId,
//     redirect_uri: config?.oidcRedirectUrl,
//   };

//   return (
//     <AuthProvider {...oidcConfig}>
//       <AppRouter />
//     </AuthProvider>
//   );
// }

// export default App;

import React, { Suspense } from 'react';
import AppRouter from './Router';
// import NoAccess from 'pages/no-access';
import './index.scss';
// import AutoLogout from 'secure/auto-logout';
// import ConfigProvider from 'context/config-provider';
// import { ROUTES, TOKEN } from 'common/constants';
// import { BrowserRouter } from 'react-router-dom';
import NoAccess from './pages/no-access';
import AutoLogout from './secure/auto-logout';
import { OIDC_PREFIX, ROUTES } from './utils/const';
import ConfigProvider from './context/config-provider';
import { hasPrefixKeyInLocalStorage } from './utils/utils';
import { Provider } from 'react-redux';
import { store } from './app/store.ts';
// import LayoutHeader from 'common/layout-header';
const AppBody = () => {
  return (
    <Suspense fallback={null}>
      {/* <BrowserRouter> */}
        <ConfigProvider>
        <Provider store={store}>
          <AppRouter/>
          </Provider>
        </ConfigProvider>
      {/* </BrowserRouter> */}
    </Suspense>
  )
  
};

const App: React.FC = () => {
  const hasToken = hasPrefixKeyInLocalStorage(OIDC_PREFIX)
  // TOKEN is not exsist
  if(!hasToken && ![ROUTES.Login, ROUTES.ChangePWD, ROUTES.FindPWD, ROUTES.Register].includes(window.location.pathname)){
    window.location.href=ROUTES.Login;
    return null;
  }
  //TODO: token is invalid
  // No Access
  if (window.location.pathname === '/noaccess') {
    return <NoAccess />;
  } else {
      
      return (
        <>
          <AutoLogout timeout={24 * 60 * 60 * 1000} />
          <AppBody />
        </>
      );
  }
};

export default App;