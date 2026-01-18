import React, { useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { FileList } from './components/FileList';
import { MonitoringDashboard } from './components/MonitoringDashboard';

type ViewType = 'files' | 'monitoring';

function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeView, setActiveView] = useState<ViewType>('files');

  const handleUploadSuccess = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Abnormal Security - File Hub</h1>
              <p className="mt-1 text-sm text-gray-500">
                File management and monitoring system
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setActiveView('files')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  activeView === 'files'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span>Files</span>
                </div>
              </button>
              <button
                onClick={() => setActiveView('monitoring')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  activeView === 'monitoring'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <span>Monitoring</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {activeView === 'files' ? (
            <div className="space-y-6">
              <div className="bg-white shadow sm:rounded-lg">
                <FileUpload onUploadSuccess={handleUploadSuccess} />
              </div>
              <div className="bg-white shadow sm:rounded-lg">
                <FileList key={refreshKey} />
              </div>
            </div>
          ) : (
            <MonitoringDashboard />
          )}
        </div>
      </main>
      <footer className="bg-white shadow mt-8">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            © 2024 File Hub. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
