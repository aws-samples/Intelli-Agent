import moment from 'moment';
import { EN_LANG, OIDC_PREFIX, OIDC_STORAGE, ZH_LANG } from './const';
import { Dispatch, SetStateAction } from 'react';
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
  const authToken = localStorage.getItem(`${OIDC_PREFIX}${oidcRes.provider}.${oidcRes.clientId}`)
  if(!authToken) return null
  return JSON.parse(authToken)    
}

export const getCredentials = () => {
  const oidcInfo = JSON.parse(localStorage.getItem(OIDC_STORAGE) || '')
  const credentials = localStorage.getItem(`oidc.${oidcInfo?.provider}.${oidcInfo?.clientId}`);
  if (!credentials) {
    return null;
  }
  return JSON.parse(credentials);
}

export  const changeLanguage = (lang: string, setLang: Dispatch<SetStateAction<string>>, i18n: any) => {
  if (lang === EN_LANG) {
    setLang(ZH_LANG);
    i18n.changeLanguage(ZH_LANG);
  } else {
    setLang(EN_LANG);
    i18n.changeLanguage(EN_LANG);
  }
};

export const removeKeysWithPrefix = (prefix: string) => {
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const key = localStorage.key(i);
    if (key && key.startsWith(prefix)) {
      localStorage.removeItem(key);
    }
  }
}
