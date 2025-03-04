import moment from 'moment';
import { OIDC_PREFIX, OIDC_STORAGE } from './const';
export const TIME_FORMAT = 'YYYY-MM-DD HH:mm:ss';

export type AlertType = 'error' | 'warning' | 'info' | 'success';
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  error: string;
}



export const alertMsg = (alertTxt: string, alertType: AlertType = 'error') => {
  const patchEvent = new CustomEvent('showAlertMsg', {
    detail: {
      alertTxt,
      alertType,
    },
  });
  window.dispatchEvent(patchEvent);
};

export const formatTime = (timeStr: string | number) => {
  if (!timeStr) {
    return '-';
  }
  return moment(timeStr).format(TIME_FORMAT);
};

export const isValidJson = (str: string) => {
  try {
    JSON.parse(str);
    return true;
  } catch (e) {
    return false;
  }
};

const nameTagAllowedPattern = /^[a-zA-Z0-9-_]+$/;
export const validateNameTagString = (input: string): boolean => {
  if (input && !nameTagAllowedPattern.test(input)) {
    return false;
  }
  return true;
};

export const hasPrefixKeyInLocalStorage = (prefix: string): boolean =>{
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith(prefix)) {
      return true;
    }
  }
  return false;
}

export const getCredentialsFromLocalStorage = () => {
  const oidc = localStorage.getItem(OIDC_STORAGE)
  if (!oidc) return null
  const oidcRes = JSON.parse(oidc)
  const authToken = localStorage.getItem(`${OIDC_PREFIX}${oidcRes.provider}.${oidcRes.client_id}`)
  if(!authToken) return null
  return JSON.parse(authToken)    
}
