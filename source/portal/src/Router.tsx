import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatBot from './pages/chatbot/ChatBot';
import Library from './pages/library/Library';
import LibraryDetail from './pages/library/LibraryDetail';
import CommonAlert from './comps/alert';
import { useAuth } from 'react-oidc-context';
import { Box, Button, Spinner } from '@cloudscape-design/components';
import { LAST_VISIT_URL } from './utils/const';
import ReSignIn from './comps/ReSignIn';
import { useTranslation } from 'react-i18next';
import SessionHistory from './pages/history/SessionHistory';
import SessionDetail from './pages/history/SessionDetail';

const LoginCallback: React.FC = () => {
  const gotoBasePage = () => {
    const lastVisitUrl = localStorage.getItem(LAST_VISIT_URL) ?? '/';
    localStorage.removeItem(LAST_VISIT_URL);
    window.location.href = `${lastVisitUrl}`;
  };
  gotoBasePage();
  return (
    <div className="page-loading">
      <Spinner />
    </div>
  );
};

const SignedInRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/signin" element={<LoginCallback />} />
        <Route path="/" element={<ChatBot />} />
        <Route path="/library" element={<Library />} />
        <Route path="/library/detail/:id" element={<LibraryDetail />} />
        <Route path="/session" element={<SessionHistory />} />
        <Route path="/session/detail/:id" element={<SessionDetail />} />
      </Routes>
      <CommonAlert />
    </BrowserRouter>
  );
};

const AppRouter = () => {
  const auth = useAuth();
  const { t } = useTranslation();
  if (auth.isLoading) {
    return (
      <div className="page-loading">
        <Spinner />
      </div>
    );
  }

  if (auth.error) {
    return (
      <>
        <ReSignIn />
        <SignedInRouter />
      </>
    );
  }

  if (auth.isAuthenticated) {
    return <SignedInRouter />;
  }
  return (
    <div className="login-container">
      <div className="text-center">
        <Box variant="h2">{t('welcome')}</Box>
        <div className="mt-10">
          <Button variant="primary" onClick={() => void auth.signinRedirect()}>
            {t('button.login')}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AppRouter;
