import axios from 'axios';
import { useContext } from 'react';
import ConfigContext, { Config } from 'src/context/config-context';
import { OIDC_PROVIDER, OIDC_STORAGE } from 'src/utils/const';
import { alertMsg } from 'src/utils/utils';

const getToken = (oidcProvider?: string, oidcClientId?: string) => {
  const oidcStorage = localStorage.getItem(
    `oidc.${oidcProvider}:${oidcClientId}`,
  );
  if (!oidcStorage) {
    return null;
  }
  return JSON.parse(oidcStorage).access_token;
}

const useAxiosRequest = () => {
  const config = useContext(ConfigContext);
  const token = getToken(config?.oidcProvider, config?.oidcClientId);
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
