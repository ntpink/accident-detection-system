import React from 'react';
import { NavLink } from 'react-router-dom';
import { ShieldAlert, Video, History, Car, Activity } from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col shrink-0 min-h-screen border-r border-slate-800 shadow-xl">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800/80 flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <ShieldAlert className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-base tracking-wide text-white">ACCIDENT AI</h1>
          <p className="text-xs text-slate-400 font-medium">Traffic Detection</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `flex items-center space-x-3 px-4 py-3 rounded-xl font-medium text-sm transition-all duration-200 ${
              isActive
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`
          }
        >
          <Video className="w-5 h-5" />
          <span>Phân tích video</span>
        </NavLink>

        <NavLink
          to="/history"
          className={({ isActive }) =>
            `flex items-center space-x-3 px-4 py-3 rounded-xl font-medium text-sm transition-all duration-200 ${
              isActive
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`
          }
        >
          <History className="w-5 h-5" />
          <span>Lịch sử phân tích</span>
        </NavLink>
      </nav>

      {/* Footer Info Box */}
      <div className="p-4 m-4 rounded-xl bg-slate-800/50 border border-slate-700/50">
        <div className="flex items-center space-x-2 text-xs font-semibold text-blue-400 mb-1">
          <Activity className="w-3.5 h-3.5" />
          <span>AI Engine</span>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          YOLO11x Accident Model + ByteTrack Vehicle Tracker
        </p>
      </div>
    </aside>
  );
}
