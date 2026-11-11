import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileVideo, Play, CheckCircle2, AlertTriangle, Loader2, ArrowRight } from 'lucide-react';
import { videoApi } from '../api';

export default function UploadPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [videoDuration, setVideoDuration] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  // Trạng thái upload và phân tích
  const [isUploading, setIsUploading] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processPercent, setProcessPercent] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [createdVideoId, setCreatedVideoId] = useState(null);

  // Tạo URL xem trước và lấy thời lượng khi chọn file
  const handleFileSelect = (file) => {
    setErrorMessage('');
    if (!file) return;

    const validExtensions = ['.mp4', '.avi', '.mov', '.mkv'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validExtensions.includes(ext)) {
      setErrorMessage(`Định dạng file không hỗ trợ (${ext}). Vui lòng chọn MP4, AVI, MOV hoặc MKV.`);
      return;
    }

    if (file.size > 500 * 1024 * 1024) {
      setErrorMessage(`Dung lượng video (${(file.size / (1024 * 1024)).toFixed(1)}MB) vượt quá giới hạn 500MB.`);
      return;
    }

    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    // Đo thời lượng video bằng thẻ Video ảo
    const tempVideo = document.createElement('video');
    tempVideo.preload = 'metadata';
    tempVideo.src = url;
    tempVideo.onloadedmetadata = () => {
      setVideoDuration(tempVideo.duration);
    };
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  // Bắt đầu quá trình tải lên và phân tích
  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadPercent(0);
    setErrorMessage('');
    setStatusMessage('Đang tải video lên máy chủ...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await videoApi.uploadVideo(formData, (percent) => {
        setUploadPercent(percent);
        if (percent === 100) {
          setStatusMessage('Đang lưu và chuẩn bị tác vụ phân tích AI...');
        }
      });

      const videoId = response.data.video_id;
      setCreatedVideoId(videoId);
      setIsUploading(false);
      setIsProcessing(true);
      setStatusMessage('Bắt đầu phân tích AI...');

      // Bắt đầu polling trạng thái mỗi 1 giây
      startPolling(videoId);
    } catch (err) {
      setIsUploading(false);
      setIsProcessing(false);
      const detail = err.response?.data?.detail || err.message || 'Lỗi không xác định khi tải video lên.';
      setErrorMessage(detail);
    }
  };

  // Polling tiến độ phân tích mỗi 1 giây
  const startPolling = (videoId) => {
    const interval = setInterval(async () => {
      try {
        const res = await videoApi.getVideoStatus(videoId);
        const { status, progress, message } = res.data;

        setProcessPercent(progress || 0);
        setStatusMessage(message || `Đang xử lý: ${progress}%`);

        if (status === 'done') {
          clearInterval(interval);
          setStatusMessage('Phân tích hoàn tất! Đang chuyển đến trang kết quả...');
          setTimeout(() => {
            navigate(`/result/${videoId}`);
          }, 800);
        } else if (status === 'error') {
          clearInterval(interval);
          setIsProcessing(false);
          setErrorMessage(message || 'Đã xảy ra sự cố trong quá trình phân tích AI.');
        }
      } catch (pollErr) {
        console.error('Lỗi khi polling:', pollErr);
      }
    }, 1000);
  };

  // Định dạng kích thước file
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Định dạng thời gian
  const formatDuration = (seconds) => {
    if (!seconds) return 'Đang đọc...';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Title & Introduction */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <h1 className="text-xl font-bold text-slate-800">Tải lên video giao thông để phân tích</h1>
        <p className="text-sm text-slate-500 mt-1 leading-relaxed">
          Hệ thống sử dụng mô hình kép (YOLO11x phát hiện tai nạn + YOLO11n ByteTrack theo dõi phương tiện).
          Video sẽ được AI phân tích trước ở chế độ nền và phát lại với bounding box mượt mà.
        </p>
      </div>

      {/* Thông báo lỗi nếu có */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 flex items-start space-x-3 text-sm animate-fadeIn">
          <AlertTriangle className="w-5 h-5 shrink-0 text-red-600 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">Lỗi: </span>
            {errorMessage}
          </div>
        </div>
      )}

      {/* Vùng Drag & Drop */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isUploading && !isProcessing && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 ${
          isDragging
            ? 'border-blue-500 bg-blue-50/60 scale-[1.01]'
            : 'border-slate-300 hover:border-blue-400 bg-white hover:bg-slate-50/50'
        } ${isUploading || isProcessing ? 'pointer-events-none opacity-80' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".mp4,.avi,.mov,.mkv"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
        />

        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center shadow-inner">
            <UploadCloud className="w-8 h-8" />
          </div>

          <div>
            <p className="text-base font-semibold text-slate-800">
              Kéo & thả file video vào đây hoặc <span className="text-blue-600 underline">chọn từ máy tính</span>
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Hỗ trợ định dạng: MP4, AVI, MOV, MKV (Tối đa 500MB)
            </p>
          </div>
        </div>
      </div>

      {/* Thông tin video đã chọn & Preview */}
      {selectedFile && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">Thông tin video đã chọn</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center space-x-3">
              <FileVideo className="w-8 h-8 text-blue-600 shrink-0" />
              <div className="truncate">
                <p className="text-xs text-slate-400 font-medium">Tên file</p>
                <p className="text-sm font-semibold text-slate-800 truncate" title={selectedFile.name}>
                  {selectedFile.name}
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0 text-xs font-bold">
                MB
              </div>
              <div>
                <p className="text-xs text-slate-400 font-medium">Dung lượng</p>
                <p className="text-sm font-semibold text-slate-800">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                <Play className="w-4 h-4 fill-current" />
              </div>
              <div>
                <p className="text-xs text-slate-400 font-medium">Thời lượng</p>
                <p className="text-sm font-semibold text-slate-800">{formatDuration(videoDuration)}</p>
              </div>
            </div>
          </div>

          {/* Video Preview */}
          {previewUrl && (
            <div className="mt-4 rounded-xl overflow-hidden bg-black aspect-video max-h-80 mx-auto shadow-md">
              <video src={previewUrl} controls className="w-full h-full object-contain" />
            </div>
          )}

          {/* Khu vực Tiến trình (Upload / AI Analysis) */}
          {(isUploading || isProcessing) && (
            <div className="mt-6 p-5 rounded-xl bg-blue-50/80 border border-blue-200/80 space-y-3">
              <div className="flex items-center justify-between text-sm font-semibold text-slate-800">
                <span className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  <span>{statusMessage}</span>
                </span>
                <span className="text-blue-700 font-bold">
                  {isUploading ? `${uploadPercent}%` : `${processPercent}%`}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-3 bg-blue-200/60 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full transition-all duration-300 shadow-sm"
                  style={{ width: `${isUploading ? uploadPercent : processPercent}%` }}
                ></div>
              </div>

              <p className="text-xs text-slate-500 italic">
                {isProcessing
                  ? 'Quá trình phân tích đang chạy ở chế độ nền. Trang sẽ tự động chuyển sang Kết quả khi hoàn tất...'
                  : 'Đang tải file lên máy chủ...'}
              </p>
            </div>
          )}

          {/* Nút Bắt đầu phân tích */}
          {!isUploading && !isProcessing && (
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={handleStartAnalysis}
                className="flex items-center space-x-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm shadow-md shadow-blue-600/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <span>Bắt đầu phân tích</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
