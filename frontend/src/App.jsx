import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import UploadPage from './pages/UploadPage';
import ResultPage from './pages/ResultPage';
import HistoryPage from './pages/HistoryPage';

function AppLayout() {
  const location = useLocation();

  // Tạo tiêu đề động theo đường dẫn
  const getHeaderInfo = () => {
    if (location.pathname.startsWith('/result')) {
      return {
        title: 'Chi tiết kết quả phân tích',
        subtitle: 'Video kèm bounding box bám xe và các đoạn cảnh báo tai nạn',
      };
    }
    if (location.pathname === '/history') {
      return {
        title: 'Lịch sử phân tích',
        subtitle: 'Quản lý và tra cứu các video giao thông đã xử lý',
      };
    }
    return {
      title: 'Phân tích video giao thông',
      subtitle: 'Tải video lên để phát hiện và cảnh báo tai nạn bằng AI',
    };
  };

  const { title, subtitle } = getHeaderInfo();

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar trái cố định */}
      <Sidebar />

      {/* Vùng nội dung chính */}
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title={title} subtitle={subtitle} />

        <main className="flex-1 p-8">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/upload" element={<Navigate to="/" replace />} />
            <Route path="/result/:id" element={<ResultPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
