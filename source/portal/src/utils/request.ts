import Axios, { AxiosRequestConfig, AxiosResponse } from 'axios';
import { reject } from 'lodash';
import { alertMsg, ApiResponse } from './utils';

const BASE_URL = '/api';

const axios = Axios.create({
  baseURL: BASE_URL,
  timeout: 100000,
});

// GET Request
export function getRequest<T>(url: string, params?: any): Promise<T> {
  return axios
    .get<ApiResponse<T>>(`${url}`, {
      params,
    })
    .then((response: AxiosResponse) => {
      const apiRes: ApiResponse<T> = response.data;
      if (apiRes.success) {
        return response.data;
      } else {
        alertMsg(apiRes.message);
        throw new Error(response.data.message || 'Error');
      }
    })
    .catch((err) => {
      errMsg(err);
      reject(err);
    });
}

// POST Request
export function postRequest<T>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig,
): Promise<T> {
  return axios
    .post<ApiResponse<T>>(`${url}`, data, config)
    .then((response: AxiosResponse) => {
      const apiRes: ApiResponse<T> = response.data;
      if (apiRes.success) {
        return response.data;
      } else {
        alertMsg(apiRes.message);
        throw new Error(response.data.message || 'Error');
      }
    })
    .catch((err) => {
      errMsg(err);
      reject(err);
      throw new Error(err?.response?.data?.error || 'Error');
    });
}

// PUT Request
export function putRequest<T>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig,
): Promise<T> {
  return axios
    .put<ApiResponse<T>>(`${url}`, data, config)
    .then((response: AxiosResponse) => {
      const apiRes: ApiResponse<T> = response.data;
      if (apiRes.success) {
        return response.data;
      } else {
        alertMsg(apiRes.message);
        throw new Error(response.data.message || 'Error');
      }
    })
    .catch((err) => {
      errMsg(err);
      reject(err);
    });
}

// DELETE Request
export function deleteRequest<T>(url: string, data?: any): Promise<T> {
  return axios
    .delete<ApiResponse<T>>(`${url}`, data)
    .then((response: AxiosResponse) => {
      const apiRes: ApiResponse<T> = response.data;
      if (apiRes.success) {
        return response.data;
      } else {
        alertMsg(apiRes.message);
        throw new Error(response.data.message || 'Error');
      }
    })
    .catch((err) => {
      errMsg(err);
      reject(err);
    });
}

// Handler api request and return data
export const apiRequest = (
  fecth: 'get' | 'post' | 'put' | 'delete',
  url: string,
  param?: string | Record<string, any> | undefined,
) => {
  return new Promise((resolve, reject) => {
    switch (fecth) {
      case 'get':
        getRequest(url, param)
          .then((response) => {
            resolve(response);
          })
          .catch((err) => {
            reject(err);
          });
        break;
      case 'post':
        postRequest(url, param)
          .then((response) => {
            resolve(response);
          })
          .catch((err) => {
            reject(err);
          });
        break;
      case 'put':
        putRequest(url, param)
          .then((response) => {
            resolve(response);
          })
          .catch((err) => {
            reject(err);
          });
        break;
      case 'delete':
        deleteRequest(url, param)
          .then((response) => {
            resolve(response);
          })
          .catch((err) => {
            reject(err);
          });
        break;
      default:
        reject('unknown request');
        break;
    }
  });
};

// Error handler
function errMsg(err: { response: { status: any; data: ApiResponse<null> } }) {
  if (err?.response) {
    switch (err.response.status) {
      case 400:
        alertMsg(err.response?.data?.message);
        break;
      case 401:
        alertMsg('Unauthorized, please log in');
        break;
      case 403:
        alertMsg('Access denied');
        break;
      case 404:
        alertMsg('Request address not found');
        break;
      case 408:
        alertMsg('Request timed out');
        break;
      case 429:
        alertMsg('Too many requests');
        break;
      case 500:
        alertMsg('Internal server error');
        break;
      case 501:
        alertMsg('Service not implemented');
        break;
      case 502:
        alertMsg('Gateway error');
        break;
      case 503:
        alertMsg('Service is not available');
        break;
      case 504:
        alertMsg('Gateway timeout');
        break;
      case 505:
        alertMsg('HTTP version not supported');
        break;
      default:
        alertMsg('Network error please try again later');
        break;
    }
  } else {
    alertMsg('Network error please try again later');
  }
}
