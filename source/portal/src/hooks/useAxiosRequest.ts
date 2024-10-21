import axios from 'axios';
import { User } from 'oidc-client-ts';
import { useContext } from 'react';
import ConfigContext from 'src/context/config-context';
import { alertMsg } from 'src/utils/utils';

function getUser(authority?: string, clientId?: string) {
  const oidcStorage = localStorage.getItem(
    `oidc.user:${authority}:${clientId}`,
  );
  if (!oidcStorage) {
    return null;
  }
  return User.fromStorageString(oidcStorage);
}

const useAxiosRequest = () => {
  const config = useContext(ConfigContext);
  const user = getUser(config?.oidcIssuer, config?.oidcClientId);
  const token = user?.id_token;
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
          Authorization: `Bearer ${token}`,
          // 'x-api-key': config?.apiKey,
          // 'author': user?.profile.email || 'anonumous user'
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

export default useAxiosRequest;
