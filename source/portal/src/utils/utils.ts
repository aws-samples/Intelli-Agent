import moment from 'moment';
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
