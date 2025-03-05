import axios from 'axios';
import { useContext } from 'react';
import ConfigContext from 'src/context/config-context';
import { alertMsg } from 'src/utils/utils';

const useAxiosAuthRequest = () => {
  const config = useContext(ConfigContext);
  // const user = getUser(config?.oidcIssuer, config?.oidcClientId);
  // const token = user?.id_token;
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
          ...headers
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

export default useAxiosAuthRequest;
