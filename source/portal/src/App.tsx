import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatBot from './pages/chatbot/ChatBot';
import Library from './pages/Library';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatBot />} />
        <Route path="/library" element={<Library />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
