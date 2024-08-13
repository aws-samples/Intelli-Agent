import { useContext } from 'react';
import ConfigContext from './context/config-context';
import { AuthProvider } from 'react-oidc-context';
import AppRouter from './Router';
import { WebStorageStateStore } from 'oidc-client-ts';
import { ROUTES } from './utils/const';

function App() {
  const config = useContext(ConfigContext);
  const token = localStorage.getItem("token")
  const oidcConfig = {
    userStore: new WebStorageStateStore({ store: window.localStorage }),
    scope: 'openid email profile',
    automaticSilentRenew: true,
    authority: config?.oidcIssuer,
    client_id: config?.oidcClientId,
    redirect_uri: config?.oidcRedirectUrl,
  };
  // TOKEN is not exsist
  if((token == '' || token == null) && ![ROUTES.Login, ROUTES.ChangePWD, ROUTES.FindPWD, ROUTES.Register].includes(window.location.pathname)){
    window.location.href=ROUTES.Login;
  }

  return (
    <AuthProvider {...oidcConfig}>
      <AppRouter />
    </AuthProvider>
  );
}

export default App;
