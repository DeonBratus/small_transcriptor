import React, { useState } from 'react';
import { Mic, FileText, Settings, Activity } from 'lucide-react';
import TranscriptionTab from './components/TranscriptionTab';
import EvaluationTab from './components/EvaluationTab';
import StatusBar from './components/StatusBar';

function App() {
  const [activeTab, setActiveTab] = useState('transcription');
  const [servicesStatus, setServicesStatus] = useState({
    transcriptor: false,
    aiJudge: false,
    ollama: false
  });

  const tabs = [
    {
      id: 'transcription',
      name: 'Транскрибация',
      icon: Mic,
      component: TranscriptionTab
    },
    {
      id: 'evaluation',
      name: 'Оценка презентаций',
      icon: FileText,
      component: EvaluationTab
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-primary-600 rounded-lg">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">AI Transcriptor</h1>
                <p className="text-sm text-gray-500">Транскрибация и оценка презентаций</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <StatusBar 
                servicesStatus={servicesStatus} 
                setServicesStatus={setServicesStatus}
              />
              <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{tab.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {tabs.map((tab) => {
          const Component = tab.component;
          return (
            activeTab === tab.id && (
              <Component key={tab.id} servicesStatus={servicesStatus} />
            )
          );
        })}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-500">
            <p>© 2024 AI Transcriptor. Powered by Vosk, Ollama & React.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
