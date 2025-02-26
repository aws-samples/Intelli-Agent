import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatBot from './pages/chatbot/ChatBot';
import Library from './pages/library/Library';
import LibraryDetail from './pages/library/LibraryDetail';
import CommonAlert from './comps/alert';
import { useTranslation } from 'react-i18next';
import SessionHistory from './pages/history/SessionHistory';
import SessionDetail from './pages/history/SessionDetail';
import PromptList from './pages/prompts/PromptList';
import ChatbotManagement from './pages/chatbotManagement/ChatbotManagement';

import LoginCallback from './comps/LoginCallback';
import Intention from './pages/intention/Intention';
import IntentionDetail from './pages/intention/IntentionDetail';
import Home from './pages/home/Home';
import ChatbotDetail from './pages/chatbotManagement/ChatbotDetail';
import CustomerService from './pages/customService/CustomerService';

const SignedInRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/signin" element={<LoginCallback />} />
        <Route path="/chats" element={<ChatBot />} />
        <Route path="/" element={<Home />} />
        <Route path="/library" element={<Library />} />
        <Route path="/library/detail/:id" element={<LibraryDetail />} />
        <Route path="/sessions" element={<SessionHistory />} />
        <Route path="/session/detail/:id" element={<SessionDetail />} />
        <Route path="/prompts" element={<PromptList />} />
        <Route path="/intention" element={<Intention />} />
        <Route path="/intention/detail/:id" element={<IntentionDetail />} />
        <Route path="/chatbot-management" element={<ChatbotManagement />} />
        <Route path="/chatbot/detail/:id" element={<ChatbotDetail />} />
        <Route path="/workspace" element={<CustomerService />} />
        <Route path="/workspace/chat/:id" element={<CustomerService />} />
      </Routes>
      <CommonAlert />
    </BrowserRouter>
  );
};

const AppRouter = () => {
  useTranslation();

  return <SignedInRouter />;
};

export default AppRouter;
