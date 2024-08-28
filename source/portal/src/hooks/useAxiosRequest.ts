import axios from 'axios';
import { useContext } from 'react';
import ConfigContext from 'src/context/config-context';
import { alertMsg } from 'src/utils/utils';

const useAxiosRequest = () => {
  const config = useContext(ConfigContext);
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
          'x-api-key': config?.apiKey,
          'author': user?.profile.email || 'anonumous user'
          // 'x-api-key': "mDX4kERuV4Mv41ctQD4WX1Q9"
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
