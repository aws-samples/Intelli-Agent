import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatBot from './pages/chatbot/ChatBot';
import Library from './pages/library/Library';
import AddLibrary from './pages/library/AddLibrary';
import LibraryDetail from './pages/library/LibraryDetail';
import CommonAlert from './comps/alert';
import { useAuth } from 'react-oidc-context';
import { Box, Button, Spinner } from '@cloudscape-design/components';
import { LAST_VISIT_URL } from './utils/const';
import ReSignIn from './comps/ReSignIn';

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
        <Route path="/library/add" element={<AddLibrary />} />
      </Routes>
      <CommonAlert />
    </BrowserRouter>
  );
};

const AppRouter = () => {
  const auth = useAuth();
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
        <Box variant="h2">Welcome to LLM Bot</Box>
        <div className="mt-10">
          <Button onClick={() => void auth.signinRedirect()}>
            Log in to LLM Bot
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AppRouter;
