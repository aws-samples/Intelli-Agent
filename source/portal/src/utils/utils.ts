export type AlertType = 'error' | 'warning' | 'info' | 'success';
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  error: string;
}

export const WebsocketUrl = 'http://localhost:8080/ws';

export const alertMsg = (alertTxt: string, alertType: AlertType = 'error') => {
  const patchEvent = new CustomEvent('showAlertMsg', {
    detail: {
      alertTxt,
      alertType,
    },
  });
  window.dispatchEvent(patchEvent);
};
