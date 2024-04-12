import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatBot from './pages/chatbot/ChatBot';
import Library from './pages/Library';
import ConfigProvider from './context/config-provider';

function App() {
  return (
    <ConfigProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChatBot />} />
          <Route path="/library" element={<Library />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
