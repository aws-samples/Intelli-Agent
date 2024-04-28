import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatBot from './pages/chatbot/ChatBot';
import Library from './pages/library/Library';
import ConfigProvider from './context/config-provider';
import AddLibrary from './pages/library/AddLibrary';
import LibraryDetail from './pages/library/LibraryDetail';
import CommonAlert from './comps/alert';

function App() {
  return (
    <ConfigProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChatBot />} />
          <Route path="/library" element={<Library />} />
          <Route path="/library/detail/:id" element={<LibraryDetail />} />
          <Route path="/library/add" element={<AddLibrary />} />
        </Routes>
        <CommonAlert />
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
