export type AlertType = 'error' | 'warning' | 'info' | 'success';
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  error: string;
}

export const WebsocketUrl = 'wss://foihh9hct6.execute-api.us-east-1.amazonaws.com/prod/';

export const alertMsg = (alertTxt: string, alertType: AlertType = 'error') => {
  const patchEvent = new CustomEvent('showAlertMsg', {
    detail: {
      alertTxt,
      alertType,
    },
  });
  window.dispatchEvent(patchEvent);
};
