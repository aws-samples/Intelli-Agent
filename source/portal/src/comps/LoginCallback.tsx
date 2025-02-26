import React, { useEffect } from 'react';
import { Spinner } from '@cloudscape-design/components';

const LoginCallback: React.FC = () => {
  useEffect(() => {
    // Simply redirect to home page
    window.location.href = '/';
  }, []);

  return (
    <div className="page-loading">
      <Spinner />
    </div>
  );
};

export default LoginCallback;
