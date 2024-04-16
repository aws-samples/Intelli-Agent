import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatBot from './pages/chatbot/ChatBot';
import Library from './pages/library/Library';
import ConfigProvider from './context/config-provider';
import AddLibrary from './pages/library/AddLibrary';

function App() {
  return (
    <ConfigProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChatBot />} />
          <Route path="/library" element={<Library />} />
          <Route path="/library/add" element={<AddLibrary />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
