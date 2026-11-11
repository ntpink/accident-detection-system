import axios from 'axios';

// Cấu hình base URL thông qua Vite proxy hoặc trực tiếp backend
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const videoApi = {
  // Tải lên video mới
  uploadVideo: (formData, onProgress) => {
    return api.post('/videos', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
  },

  // Polling trạng thái xử lý
  getVideoStatus: (id) => api.get(`/videos/${id}/status`),

  // Danh sách lịch sử
  listVideos: () => api.get('/videos'),

  // Chi tiết video và các sự kiện
  getVideoDetails: (id) => api.get(`/videos/${id}`),

  // Lấy JSON kết quả chi tiết từng frame
  getVideoResult: (id) => api.get(`/videos/${id}/result`),

  // Xóa video
  deleteVideo: (id) => api.delete(`/videos/${id}`),

  // Đường dẫn stream video
  getStreamUrl: (id) => `/api/videos/${id}/stream`,

  // Đường dẫn ảnh bằng chứng
  getEvidenceUrl: (relPath) => `/${relPath}`,
};

export default api;
