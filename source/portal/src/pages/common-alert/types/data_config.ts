export type AlertType = 'error' | 'warning' | 'info' | 'success';

export const COMMON_ALERT_TYPE = {
  Success: 'success',
  Error: 'error',
  Warning: 'warning',
  Info: 'info',
};

export interface COMMON_ALERT_PROPS {
  alertTxt: string;
  alertType: AlertType;
}
