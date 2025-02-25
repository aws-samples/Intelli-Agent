import axios from 'axios';
import { refreshAccessToken, logout } from './authing';
import { API_URL, OIDC_REDIRECT_URL, TOKEN } from 'src/utils/const';
// import { API_URL, OIDC_REDIRECT_URL, TOKEN } from 'common/constants';
// import { Constant } from 'common/constants';

const apiClient = axios.create({
  baseURL: '',
  // withCredentials: true,
});

apiClient.interceptors.request.use(
  async (config: any) => {
    config.baseURL = localStorage.getItem(API_URL);
    config.headers['Content-Type'] = 'application/json';
    // config.headers['Access-Control-Allow-Origin'] = '*';
    // config.withCredentials = true;
    const excludedPaths = ['/login'];
    if (excludedPaths.some(path => config.url.includes(path))) {
      config.headers['Authorization'] = `Auth-api-key`;
      return config;
    }
    let token = localStorage.getItem(TOKEN);
    if(token){
      const accessToken = JSON.parse(token).access_token
      if (accessToken){
        // if(isTokenExpired(accessToken)) {
        if(false) {
          try {
            token = await refreshAccessToken();
          } catch (error) {
            logout();
            window.location.href = '/login';
            return Promise.reject(error);
          }
        } else {
          // config.headers['Access-Control-Allow-Origin'] = ['*'];
          config.headers['Authorization'] = `Bearer ${accessToken}`;
          config.headers['OidcIssuer'] = localStorage.getItem(OIDC_REDIRECT_URL);

        }
      }
      return config;
      // return 
    } else {
      const source = axios.CancelToken.source();
      config.cancelToken = source.token;
      window.location.href = '/login';
      return config;
    }
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default apiClient;
