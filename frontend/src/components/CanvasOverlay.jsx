import React, { useEffect, useRef } from 'react';

/**
 * Component Canvas phủ lên Video:
 * - Đồng bộ theo video.requestVideoFrameCallback (fallback requestAnimationFrame)
 * - Tự động tính toán scale và trừ phần letterbox của video (object-fit: contain)
 * - Nội suy tuyến tính (Linear Interpolation) + EMA smoothing giúp bounding box bám xe mượt mà, không rung
 * - Hỗ trợ màn hình Retina sắc nét (devicePixelRatio)
 */
export default function CanvasOverlay({
  videoRef,
  framesData = [],
  eventsData = [],
  showAccidents = true,
  showVehicles = true,
  onAccidentStateChange,
}) {
  const canvasRef = useRef(null);
  const emaBoxesRef = useRef({}); // Lưu trữ tọa độ mượt EMA theo ID: { [trackId]: [x1, y1, x2, y2] }
  const lastAccidentStateRef = useRef(false);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    let animationId = null;
    let rVFCId = null;

    // Tìm 2 frame lân cận và tỷ lệ nội suy alpha theo mediaTime
    const getInterpolatedData = (currentTime) => {
      if (!framesData || framesData.length === 0) {
        return { vehicles: [], accidents: [] };
      }

      // Tìm vị trí frame gần nhất
      let low = 0;
      let high = framesData.length - 1;

      if (currentTime <= framesData[0].t) {
        return framesData[0];
      }
      if (currentTime >= framesData[high].t) {
        return framesData[high];
      }

      // Binary search tìm chỉ số mốc thời gian
      while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        if (framesData[mid].t < currentTime) {
          low = mid + 1;
        } else {
          high = mid - 1;
        }
      }

      const prevIndex = Math.max(0, low - 1);
      const nextIndex = Math.min(framesData.length - 1, low);

      const frameA = framesData[prevIndex];
      const frameB = framesData[nextIndex];

      const dt = frameB.t - frameA.t;
      const alpha = dt > 0.0001 ? Math.min(1.0, Math.max(0.0, (currentTime - frameA.t) / dt)) : 0.0;

      // 1. Nội suy cho các xe (khớp theo ID xe)
      const vehicleMapB = new Map();
      (frameB.vehicles || []).forEach((v) => vehicleMapB.set(v.id, v));

      const interpolatedVehicles = (frameA.vehicles || []).map((vA) => {
        const vB = vehicleMapB.get(vA.id);
        if (vB) {
          // Cả 2 frame đều có xe này -> Nội suy tuyến tính tọa độ box
          const bA = vA.box;
          const bB = vB.box;
          return {
            id: vA.id,
            cls: vA.cls,
            box: [
              bA[0] + (bB[0] - bA[0]) * alpha,
              bA[1] + (bB[1] - bA[1]) * alpha,
              bA[2] + (bB[2] - bA[2]) * alpha,
              bA[3] + (bB[3] - bA[3]) * alpha,
            ],
          };
        }
        return vA;
      });

      // Thêm các xe mới chỉ xuất hiện ở frameB nếu alpha > 0.5
      if (alpha > 0.5) {
        const existingIds = new Set(interpolatedVehicles.map((v) => v.id));
        (frameB.vehicles || []).forEach((vB) => {
          if (!existingIds.has(vB.id)) {
            interpolatedVehicles.push(vB);
          }
        });
      }

      // 2. Với accident box: dùng box có conf cao hơn hoặc gần nhất
      const accidents = (frameB.accidents && frameB.accidents.length > 0 && alpha >= 0.5)
        ? frameB.accidents
        : (frameA.accidents || []);

      return {
        vehicles: interpolatedVehicles,
        accidents: accidents,
      };
    };

    // Hàm render chính trên từng frame hiển thị của video
    const render = (mediaTime) => {
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const containerWidth = canvas.clientWidth;
      const containerHeight = canvas.clientHeight;
      const videoWidth = video.videoWidth || 1920;
      const videoHeight = video.videoHeight || 1080;

      // Xử lý màn hình Retina sắc nét
      const dpr = window.devicePixelRatio || 1;
      if (canvas.width !== containerWidth * dpr || canvas.height !== containerHeight * dpr) {
        canvas.width = containerWidth * dpr;
        canvas.height = containerHeight * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, containerWidth, containerHeight);

      // Tính toán vùng hiển thị thực tế của video (loại bỏ phần viền đen letterbox)
      const containerRatio = containerWidth / containerHeight;
      const videoRatio = videoWidth / videoHeight;
      let renderWidth = containerWidth;
      let renderHeight = containerHeight;
      let offsetX = 0;
      let offsetY = 0;

      if (containerRatio > videoRatio) {
        renderHeight = containerHeight;
        renderWidth = containerHeight * videoRatio;
        offsetX = (containerWidth - renderWidth) / 2;
      } else {
        renderWidth = containerWidth;
        renderHeight = containerWidth / videoRatio;
        offsetY = (containerHeight - renderHeight) / 2;
      }

      // Lấy dữ liệu box đã được nội suy theo thời gian hiện tại
      const { vehicles, accidents } = getInterpolatedData(mediaTime);

      // Kiểm tra xem thời điểm hiện tại có thuộc vụ tai nạn nào không
      let isAccidentActive = false;
      for (const ev of eventsData) {
        if (mediaTime >= ev.start && mediaTime <= ev.end) {
          isAccidentActive = true;
          break;
        }
      }
      if (accidents.length > 0) {
        isAccidentActive = true;
      }

      if (isAccidentActive !== lastAccidentStateRef.current) {
        lastAccidentStateRef.current = isAccidentActive;
        if (onAccidentStateChange) {
          onAccidentStateChange(isAccidentActive);
        }
      }

      // Vẽ Bounding Box Phương Tiện (Xe)
      if (showVehicles && vehicles && vehicles.length > 0) {
        ctx.lineWidth = 1.8;
        ctx.font = 'bold 11px Inter, sans-serif';

        vehicles.forEach((v) => {
          const rawBox = v.box; // [nx1, ny1, nx2, ny2]
          const trackKey = `v_${v.id}`;

          // Áp dụng EMA smoothing nhẹ (alpha = 0.3)
          let smBox = emaBoxesRef.current[trackKey];
          if (!smBox) {
            smBox = [...rawBox];
          } else {
            const beta = 0.25;
            smBox = [
              smBox[0] * beta + rawBox[0] * (1 - beta),
              smBox[1] * beta + rawBox[1] * (1 - beta),
              smBox[2] * beta + rawBox[2] * (1 - beta),
              smBox[3] * beta + rawBox[3] * (1 - beta),
            ];
          }
          emaBoxesRef.current[trackKey] = smBox;

          const x = offsetX + smBox[0] * renderWidth;
          const y = offsetY + smBox[1] * renderHeight;
          const w = (smBox[2] - smBox[0]) * renderWidth;
          const h = (smBox[3] - smBox[1]) * renderHeight;

          // Màu xanh dương hiện đại cho xe
          ctx.strokeStyle = '#38bdf8'; // sky-400
          ctx.strokeRect(x, y, w, h);

          // Nhãn xe: "car #5"
          const label = `${v.cls} #${v.id}`;
          const textWidth = ctx.measureText(label).width;
          const tagHeight = 16;
          const tagY = Math.max(offsetY, y - tagHeight);

          ctx.fillStyle = '#0284c7'; // sky-600
          ctx.fillRect(x, tagY, textWidth + 8, tagHeight);
          ctx.fillStyle = '#ffffff';
          ctx.fillText(label, x + 4, tagY + 12);
        });
      }

      // Vẽ Bounding Box Tai Nạn (Accident)
      if (showAccidents && accidents && accidents.length > 0) {
        ctx.lineWidth = 3.5;
        ctx.font = 'bold 13px Inter, sans-serif';

        accidents.forEach((acc, aIdx) => {
          const rawBox = acc.box;
          const trackKey = `acc_${aIdx}`;

          let smBox = emaBoxesRef.current[trackKey];
          if (!smBox) {
            smBox = [...rawBox];
          } else {
            const beta = 0.2;
            smBox = [
              smBox[0] * beta + rawBox[0] * (1 - beta),
              smBox[1] * beta + rawBox[1] * (1 - beta),
              smBox[2] * beta + rawBox[2] * (1 - beta),
              smBox[3] * beta + rawBox[3] * (1 - beta),
            ];
          }
          emaBoxesRef.current[trackKey] = smBox;

          const x = offsetX + smBox[0] * renderWidth;
          const y = offsetY + smBox[1] * renderHeight;
          const w = (smBox[2] - smBox[0]) * renderWidth;
          const h = (smBox[3] - smBox[1]) * renderHeight;

          // Vùng đổ màu đỏ bán trong suốt
          ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
          ctx.fillRect(x, y, w, h);

          // Viền đỏ dày nổi bật
          ctx.strokeStyle = '#ef4444'; // red-500
          ctx.strokeRect(x, y, w, h);

          // Nhãn tai nạn: "ACCIDENT 92%"
          const confPercent = Math.round((acc.conf || 0.9) * 100);
          const label = `ACCIDENT ${confPercent}%`;
          const textWidth = ctx.measureText(label).width;
          const tagHeight = 22;
          const tagY = Math.max(offsetY, y - tagHeight);

          ctx.fillStyle = '#dc2626'; // red-600
          ctx.fillRect(x, tagY, textWidth + 12, tagHeight);
          ctx.fillStyle = '#ffffff';
          ctx.fillText(label, x + 6, tagY + 16);
        });
      }

      ctx.restore();
    };

    // Vòng lặp đồng bộ frame
    const onFrame = (now, metadata) => {
      const mediaTime = metadata ? metadata.mediaTime : video.currentTime;
      render(mediaTime);

      if (video.requestVideoFrameCallback) {
        rVFCId = video.requestVideoFrameCallback(onFrame);
      } else {
        animationId = requestAnimationFrame(() => onFrame(performance.now(), null));
      }
    };

    if (video.requestVideoFrameCallback) {
      rVFCId = video.requestVideoFrameCallback(onFrame);
    } else {
      animationId = requestAnimationFrame(() => onFrame(performance.now(), null));
    }

    // Render 1 lần ngay lập tức khi seek hoặc pause
    const handleSeeked = () => render(video.currentTime);
    video.addEventListener('seeked', handleSeeked);
    video.addEventListener('timeupdate', handleSeeked);

    return () => {
      if (rVFCId && video.cancelVideoFrameCallback) {
        video.cancelVideoFrameCallback(rVFCId);
      }
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
      video.removeEventListener('seeked', handleSeeked);
      video.removeEventListener('timeupdate', handleSeeked);
    };
  }, [videoRef, framesData, eventsData, showAccidents, showVehicles, onAccidentStateChange]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none z-10"
    />
  );
}
