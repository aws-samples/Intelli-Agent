import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatBot from './pages/chatbot/ChatBot';
import Library from './pages/library/Library';
import LibraryDetail from './pages/library/LibraryDetail';
import CommonAlert from './comps/alert';
import { useAuth } from 'react-oidc-context';
import { Box, Button, Spinner } from '@cloudscape-design/components';
import ReSignIn from './comps/ReSignIn';
import { useTranslation } from 'react-i18next';
import SessionHistory from './pages/history/SessionHistory';
import SessionDetail from './pages/history/SessionDetail';
import PromptList from './pages/prompts/PromptList';
import LoginCallback from './comps/LoginCallback';
import Login from './pages/login';
import FindPWD from './pages/find-pwd';
import Register from './pages/register';
import ChangePWD from './pages/change-pwd';
import { ROUTES } from './utils/const';

const SignedInRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={ROUTES.Login} element={<Login />} />
        <Route path={ROUTES.FindPWD}  element={<FindPWD />} />
        <Route path={ROUTES.Register}  element={<Register />} />
        <Route path={ROUTES.ChangePWD}  element={<ChangePWD />} />
        <Route path={ROUTES.LoginCallback}  element={<LoginCallback />} />
        <Route path={ROUTES.ChatBot} element={<ChatBot />} />
        <Route path={ROUTES.Library}  element={<Library />} />
        <Route path={ROUTES.LibraryDetail}  element={<LibraryDetail />} />
        <Route path={ROUTES.SessionHistory}  element={<SessionHistory />} />
        <Route path={ROUTES.SessionDetail}  element={<SessionDetail />} />
        <Route path={ROUTES.PromptList}  element={<PromptList />} />
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

  // if (auth.isAuthenticated) {
  //   return <SignedInRouter />;
  // }
  return (
    <SignedInRouter />
    // <Login />
    // <div className="login-container">
    //   <div className="text-center">
    //     <Box variant="h2">{t('welcome')}</Box>
    //     <div className="mt-10">
    //       <Button variant="primary" onClick={() => void auth.signinRedirect()}>
    //         {t('button.login')}
    //       </Button>
    //     </div>
    //   </div>
    // </div>
  );
};

export default AppRouter;
