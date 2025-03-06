import axios from 'axios';
<<<<<<< HEAD
// import { User } from 'oidc-client-ts';
=======
>>>>>>> abd872d66b80cae074cbce116847b164721f430b
import { useContext } from 'react';
import ConfigContext, { Config } from 'src/context/config-context';
import { OIDC_PROVIDER, OIDC_STORAGE } from 'src/utils/const';
import { alertMsg } from 'src/utils/utils';

<<<<<<< HEAD
// function getUser(authority?: string, clientId?: string) {
//   const oidcStorage = localStorage.getItem(
//     `oidc.user:${authority}:${clientId}`,
//   );
//   if (!oidcStorage) {
//     return null;
//   }
//   return User.fromStorageString(oidcStorage);
// }

const getToken = (oidcProvider?: string, oidcClientId?: string) => {
  const oidcStorage = localStorage.getItem(
    `oidc.${oidcProvider}:${oidcClientId}`,
  );
  if (!oidcStorage) {
    return null;
  }
  return JSON.parse(oidcStorage).access_token;
  // switch(oidcProvider){
  //   case 'Authing':
  //     return JSON.parse(oidcStorage).access_token;
  //   default:
  //     return JSON.parse(oidcStorage).access_token;
  // }
 
}

const useAxiosRequest = () => {
  const config = useContext(ConfigContext);
  // const user = getUser(config?.oidcIssuer, config?.oidcClientId);
  // const token = user?.id_token;
  const token = getToken(config?.oidcProvider, config?.oidcClientId);;
=======
const useAxiosRequest = () => {
  const config = useContext(ConfigContext);

  // Mock user and token
  const mockToken = 'mock-token';

>>>>>>> abd872d66b80cae074cbce116847b164721f430b
  const sendRequest = async ({
    url = '',
    method = 'get',
    data = null,
    headers = {},
    params = {},
  }: {
    url: string;
    method: 'get' | 'post' | 'put' | 'delete';
    data?: any;
    headers?: any;
    params?: any;
  }) => {
    try {
      const response = await axios({
        method: method,
        url: `${config?.apiUrl}${url}`,
        data: data,
        params: params,
        headers: {
          ...headers,
          'Authorization': `Bearer ${token}`,
          'Oidc-Info': genHeaderOidcInfo(config)
        },
      });
      return response.data;
    } catch (error) {
      if (error instanceof Error) {
        alertMsg(error.message);
      }
      throw error;
    }
  };
  return sendRequest;
};

const genHeaderOidcInfo =(config: Config | null)=>{
  const oidc = JSON.parse(localStorage.getItem(OIDC_STORAGE) || '')
  switch(oidc.provider){
    case OIDC_PROVIDER.AUTHING:
      return JSON.stringify({
        provider: oidc?.provider,
        clientId: oidc?.client_id,
        redirectUri: oidc?.redirect_uri,
      })
    default:
      return JSON.stringify({
        provider: oidc?.provider,
        clientId: config?.oidcClientId,
        poolId: config?.oidcPoolId,
  })
}
  
}

export default useAxiosRequest;
