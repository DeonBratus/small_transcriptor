import React, { useEffect } from 'react';
import { CheckCircle, XCircle, Loader } from 'lucide-react';
import { checkServicesStatus } from '../services/api';

const StatusBar = ({ servicesStatus, setServicesStatus }) => {
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await checkServicesStatus();
        setServicesStatus(status);
      } catch (error) {
        console.error('Error checking services status:', error);
      }
    };

    // Проверяем статус сразу и затем каждые 30 секунд
    checkStatus();
    const interval = setInterval(checkStatus, 30000);

    return () => clearInterval(interval);
  }, [setServicesStatus]);

  const getStatusIcon = (status) => {
    if (status === null) {
      return <Loader className="w-4 h-4 animate-spin text-gray-400" />;
    }
    return status ? (
      <CheckCircle className="w-4 h-4 text-green-500" />
    ) : (
      <XCircle className="w-4 h-4 text-red-500" />
    );
  };

  const getStatusText = (status) => {
    if (status === null) return 'Проверка...';
    return status ? 'Работает' : 'Недоступен';
  };

  const getStatusColor = (status) => {
    if (status === null) return 'text-gray-400';
    return status ? 'text-green-600' : 'text-red-600';
  };

  return (
    <div className="flex items-center space-x-4">
      <div className="flex items-center space-x-2">
        {getStatusIcon(servicesStatus.transcriptor)}
        <span className={`text-xs font-medium ${getStatusColor(servicesStatus.transcriptor)}`}>
          Транскрибатор: {getStatusText(servicesStatus.transcriptor)}
        </span>
      </div>
      
      <div className="flex items-center space-x-2">
        {getStatusIcon(servicesStatus.aiJudge)}
        <span className={`text-xs font-medium ${getStatusColor(servicesStatus.aiJudge)}`}>
          AI Judge: {getStatusText(servicesStatus.aiJudge)}
        </span>
      </div>
      
      <div className="flex items-center space-x-2">
        {getStatusIcon(servicesStatus.ollama)}
        <span className={`text-xs font-medium ${getStatusColor(servicesStatus.ollama)}`}>
          Ollama: {getStatusText(servicesStatus.ollama)}
        </span>
      </div>
    </div>
  );
};

export default StatusBar;
