import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Eye,
  Trash2,
  Calendar,
  Clock,
  AlertTriangle,
  CheckCircle,
  Loader2,
  FileVideo,
  X,
  RefreshCw,
} from 'lucide-react';
import { videoApi } from '../api';

export default function HistoryPage() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Hộp thoại xác nhận xóa
  const [deleteModalVideo, setDeleteModalVideo] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchVideos = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await videoApi.listVideos();
      setVideos(res.data || []);
      setLoading(false);
    } catch (err) {
      console.error('Lỗi khi tải lịch sử:', err);
      setError('Không thể kết nối đến máy chủ để lấy danh sách lịch sử.');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
  }, []);

  // Xóa video
  const handleDeleteConfirm = async () => {
    if (!deleteModalVideo) return;
    setIsDeleting(true);
    try {
      await videoApi.deleteVideo(deleteModalVideo.id);
      setVideos((prev) => prev.filter((v) => v.id !== deleteModalVideo.id));
      setDeleteModalVideo(null);
    } catch (err) {
      alert('Lỗi khi xóa video: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsDeleting(false);
    }
  };

  // Lọc theo từ khóa tìm kiếm
  const filteredVideos = videos.filter((v) =>
    (v.filename || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDuration = (seconds) => {
    if (!seconds) return '00:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const getStatusBadge = (status, numEvents) => {
    if (status === 'done') {
      if (numEvents > 0) {
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-700">
            <span className="w-1.5 h-1.5 rounded-full bg-red-600 animate-pulse"></span>
            <span>{numEvents} Tai nạn</span>
          </span>
        );
      }
      return (
        <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">
          <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
          <span>Bình thường</span>
        </span>
      );
    }
    if (status === 'processing') {
      return (
        <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-700">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />
          <span>Đang xử lý</span>
        </span>
      );
    }
    if (status === 'error') {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          <span>Lỗi</span>
        </span>
      );
    }
    return (
      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
        Chờ xử lý
      </span>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header & Search */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Lịch sử phân tích video</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Xem lại kết quả của các video đã được hệ thống AI xử lý
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* Ô tìm kiếm theo tên */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Tìm kiếm theo tên video..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
            />
          </div>

          {/* Nút Làm mới */}
          <button
            type="button"
            onClick={fetchVideos}
            className="p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition"
            title="Làm mới danh sách"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Bảng danh sách */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
            <p className="text-sm font-medium text-slate-500">Đang tải danh sách lịch sử...</p>
          </div>
        ) : error ? (
          <div className="py-16 text-center space-y-3 px-4">
            <AlertTriangle className="w-10 h-10 text-red-500 mx-auto" />
            <p className="text-sm text-slate-700 font-semibold">{error}</p>
            <button
              onClick={fetchVideos}
              className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition"
            >
              Thử lại
            </button>
          </div>
        ) : filteredVideos.length === 0 ? (
          <div className="py-20 text-center space-y-3 px-4">
            <FileVideo className="w-12 h-12 text-slate-300 mx-auto" />
            <p className="text-sm font-medium text-slate-600">
              {searchTerm ? 'Không tìm thấy video nào khớp với từ khóa tìm kiếm.' : 'Chưa có video nào được phân tích.'}
            </p>
            {!searchTerm && (
              <Link
                to="/"
                className="inline-block px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition shadow-sm"
              >
                Tải lên video đầu tiên
              </Link>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3.5 px-6">ID & Tên Video</th>
                  <th className="py-3.5 px-6">Ngày phân tích</th>
                  <th className="py-3.5 px-6">Thời lượng</th>
                  <th className="py-3.5 px-6">Kết quả</th>
                  <th className="py-3.5 px-6 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {filteredVideos.map((video) => (
                  <tr
                    key={video.id}
                    className="hover:bg-slate-50/60 transition-colors duration-150"
                  >
                    <td className="py-4 px-6">
                      <div className="flex items-center space-x-3">
                        <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                          <FileVideo className="w-5 h-5" />
                        </div>
                        <div className="max-w-xs truncate">
                          <p className="font-semibold text-slate-800 truncate" title={video.filename}>
                            {video.filename}
                          </p>
                          <p className="text-xs text-slate-400 font-mono">#{video.id}</p>
                        </div>
                      </div>
                    </td>

                    <td className="py-4 px-6 text-slate-500 text-xs">
                      <div className="flex items-center space-x-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{video.created_at || 'Vừa xong'}</span>
                      </div>
                    </td>

                    <td className="py-4 px-6 text-slate-600 text-xs font-mono">
                      <div className="flex items-center space-x-1.5">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        <span>{formatDuration(video.duration)}</span>
                      </div>
                    </td>

                    <td className="py-4 px-6">
                      {getStatusBadge(video.status, video.num_events)}
                    </td>

                    <td className="py-4 px-6 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        {/* Nút Xem kết quả */}
                        <Link
                          to={`/result/${video.id}`}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 font-semibold text-xs transition"
                          title="Xem kết quả phân tích"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Xem</span>
                        </Link>

                        {/* Nút Xóa */}
                        <button
                          type="button"
                          onClick={() => setDeleteModalVideo(video)}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 font-semibold text-xs transition"
                          title="Xóa video này"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Xóa</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* MODAL XÁC NHẬN XÓA */}
      {deleteModalVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-100">
            <div className="w-12 h-12 rounded-xl bg-red-100 text-red-600 flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>

            <div className="text-center space-y-1">
              <h3 className="text-base font-bold text-slate-800">Xác nhận xóa video</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Bạn có chắc chắn muốn xóa video{' '}
                <span className="font-semibold text-slate-700">"{deleteModalVideo.filename}"</span>?
                Hành động này sẽ xóa vĩnh viễn video, toàn bộ ảnh bằng chứng và kết quả phân tích.
              </p>
            </div>

            <div className="flex items-center space-x-3 pt-2">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setDeleteModalVideo(null)}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold hover:bg-slate-50 transition"
              >
                Hủy bỏ
              </button>

              <button
                type="button"
                disabled={isDeleting}
                onClick={handleDeleteConfirm}
                className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-md shadow-red-600/30 transition flex items-center justify-center space-x-1.5"
              >
                {isDeleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Xác nhận xóa</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
