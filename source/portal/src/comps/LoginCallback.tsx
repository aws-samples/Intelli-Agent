import { Spinner } from '@cloudscape-design/components';
import React, { useEffect } from 'react';
import { useAuth } from 'react-oidc-context';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { LAST_VISIT_URL } from 'src/utils/const';

const LoginCallback: React.FC = () => {
  const fetchData = useAxiosRequest();
  const auth = useAuth();
  const gotoBasePage = () => {
    const lastVisitUrl = localStorage.getItem(LAST_VISIT_URL) ?? '/';
    localStorage.removeItem(LAST_VISIT_URL);
    window.location.href = `${lastVisitUrl}`;
  };

  const createDefaultChatBotIfNotExist = async () => {
    const groupName: string[] = auth?.user?.profile?.['cognito:groups'] as any;
    const existed = await fetchData({
      url: 'chatbot-management/default-chatbot',
      method: 'get'
    })
    if(existed){
      gotoBasePage();
      return;
    }
    const data = await fetchData({
      url: 'chatbot-management/chatbots',
      method: 'post',
      data: {
        groupName: groupName?.[0] ?? 'Admin',
      },
    });
    if (data.chatbotId) {
      gotoBasePage();
    }
  };

  useEffect(() => {
    createDefaultChatBotIfNotExist();
  }, []);
  return (
    <div className="page-loading">
      <Spinner />
    </div>
  );
};

export default LoginCallback;
