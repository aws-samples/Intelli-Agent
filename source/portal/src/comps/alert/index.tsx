import { Alert } from '@cloudscape-design/components';
import classnames from 'classnames';
import React, { useEffect, useState } from 'react';

import { AlertType } from 'src/utils/utils';

interface CommonAlertProps {
  alertTxt: string;
  alertType: AlertType;
}

const CommonAlert: React.FC = () => {
  const [alertVisible, setAlertVisible] = useState(false);
  const [alertHideCls, setAlertHideCls] = useState(false);
  const [alertProps, setAlertProps] = useState({
    alertTxt: '',
    alertType: 'info',
  } as CommonAlertProps);
  useEffect(() => {
    window.addEventListener('showAlertMsg', showAlertMsg);
    return () => {
      window.removeEventListener('showAlertMsg', showAlertMsg);
    };
  }, []);

  const alertCls = classnames({
    'common-alert': true,
    'common-alert-hide': alertHideCls,
  });

  const showAlertMsg = (event: any) => {
    setAlertProps({
      alertTxt: event.detail.alertTxt,
      alertType: event.detail.alertType,
    });
    setAlertVisible(true);
    setTimeout(() => {
      setAlertHideCls(true);
      setTimeout(() => {
        setAlertVisible(false);
        setAlertHideCls(false);
      }, 900);
    }, 5000);
  };

  return (
    <div className={alertCls}>
      {alertVisible && (
        <Alert
          onDismiss={() => setAlertVisible(false)}
          dismissAriaLabel="Close"
          type={alertProps.alertType}
          dismissible={alertProps.alertType === 'success'}
        >
          {alertProps.alertTxt}
        </Alert>
      )}
    </div>
  );
};

export default CommonAlert;
