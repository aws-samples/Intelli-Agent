import {
  Alert,
  Box,
  Button,
  Modal,
  SpaceBetween,
} from '@cloudscape-design/components';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { LAST_VISIT_URL } from 'src/utils/const';

const ReSignIn: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div className="re-sign-in">
      <Modal
        className="re-sign-in-modal"
        visible={true}
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                onClick={() => {
                  localStorage.setItem(LAST_VISIT_URL, window.location.href);
                  window.location.reload();
                }}
                variant="primary"
              >
                {t('button.reload')}
              </Button>
            </SpaceBetween>
          </Box>
        }
        header={t('header.reSignIn')}
      >
        <div className="mt-10">
          <Alert statusIconAriaLabel="Error" type="warning">
            {t('header.reSignInDesc')}
          </Alert>
        </div>
      </Modal>
    </div>
  );
};

export default ReSignIn;
