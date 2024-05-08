import { useContext } from 'react';
import ConfigContext from './context/config-context';
import { AuthProvider } from 'react-oidc-context';
import AppRouter from './Router';
import { WebStorageStateStore } from 'oidc-client-ts';

function App() {
  const config = useContext(ConfigContext);
  const oidcConfig = {
    userStore: new WebStorageStateStore({ store: window.localStorage }),
    scope: 'openid email profile',
    automaticSilentRenew: true,
    authority: config?.oidcIssuer,
    client_id: config?.oidcClientId,
    redirect_uri: config?.oidcRedirectUrl,
  };

  return (
    <AuthProvider {...oidcConfig}>
      <AppRouter />
    </AuthProvider>
  );
}

export default App;
