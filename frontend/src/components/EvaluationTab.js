import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, Download, Settings, Play, Square, Eye } from 'lucide-react';
import { streamEvaluation, getAvailableModels, formatFileSize } from '../services/api';
import ResultsDisplay from './ResultsDisplay';

const EvaluationTab = ({ servicesStatus }) => {
  const [docxFile, setDocxFile] = useState(null);
  const [pptxFile, setPptxFile] = useState(null);
  const [visionModel, setVisionModel] = useState('llava');
  const [evalModel, setEvalModel] = useState('llama3.2');
  const [availableModels, setAvailableModels] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [error, setError] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [showResults, setShowResults] = useState(false);
  
  const docxInputRef = useRef(null);
  const pptxInputRef = useRef(null);
  const streamingRef = useRef(null);

  // Загружаем доступные модели при монтировании компонента
  useEffect(() => {
    const loadModels = async () => {
      try {
        const models = await getAvailableModels();
        setAvailableModels(models);
      } catch (error) {
        console.error('Error loading models:', error);
        setAvailableModels(['llama3.2', 'llava', 'mistral', 'phi3']);
      }
    };
    loadModels();
  }, []);

  // Автопрокрутка при потоковом выводе
  useEffect(() => {
    if (streamingRef.current) {
      streamingRef.current.scrollTop = streamingRef.current.scrollHeight;
    }
  }, [streamingText]);

  const handleFileSelect = (type, event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      if (type === 'docx') {
        setDocxFile(selectedFile);
      } else {
        setPptxFile(selectedFile);
      }
      setError(null);
      setStreamingText('');
      setIsComplete(false);
    }
  };

  const handleDrop = (type, event) => {
    event.preventDefault();
    const droppedFile = event.dataTransfer.files[0];
    if (droppedFile) {
      const isDocx = droppedFile.name.toLowerCase().endsWith('.docx');
      const isPptx = droppedFile.name.toLowerCase().endsWith('.pptx');
      
      if (type === 'docx' && isDocx) {
        setDocxFile(droppedFile);
      } else if (type === 'pptx' && isPptx) {
        setPptxFile(droppedFile);
      }
      setError(null);
      setStreamingText('');
      setIsComplete(false);
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const handleEvaluate = async () => {
    if (!docxFile || !pptxFile) {
      setError('Пожалуйста, загрузите оба файла (DOCX и PPTX)');
      return;
    }

    if (!servicesStatus.aiJudge || !servicesStatus.ollama) {
      setError('Сервисы AI Judge или Ollama недоступны');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setStreamingText('');
    setIsComplete(false);

    try {
      await streamEvaluation(
        docxFile,
        pptxFile,
        visionModel,
        evalModel,
        (chunk) => {
          setStreamingText(prev => prev + chunk);
        },
        () => {
          setIsComplete(true);
          setIsProcessing(false);
          setShowResults(true);
        },
        (error) => {
          setError(error);
          setIsProcessing(false);
        }
      );
    } catch (error) {
      setError(error.message || 'Ошибка при оценке презентации');
      setIsProcessing(false);
    }
  };

  const resetForm = () => {
    setDocxFile(null);
    setPptxFile(null);
    setStreamingText('');
    setError(null);
    setIsComplete(false);
    setShowResults(false);
    if (docxInputRef.current) docxInputRef.current.value = '';
    if (pptxInputRef.current) pptxInputRef.current.value = '';
  };

  const downloadResult = () => {
    if (!streamingText) return;
    
    const blob = new Blob([streamingText], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `evaluation_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };


  const FileUploadArea = ({ type, file, onFileSelect, onDrop, onDragOver, inputRef }) => {
    const isDocx = type === 'docx';
    const fileType = isDocx ? 'DOCX' : 'PPTX';
    const fileIcon = isDocx ? FileText : Eye;
    const Icon = fileIcon;

    return (
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          file
            ? 'border-green-300 bg-green-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDrop={(e) => onDrop(e)}
        onDragOver={onDragOver}
      >
        {file ? (
          <div className="space-y-2">
            <Icon className="w-10 h-10 text-green-500 mx-auto" />
            <p className="text-sm font-medium text-green-700">{file.name}</p>
            <p className="text-xs text-green-600">{formatFileSize(file.size)}</p>
            <button
              onClick={() => {
                if (isDocx) setDocxFile(null);
                else setPptxFile(null);
                if (inputRef.current) inputRef.current.value = '';
              }}
              className="text-xs text-gray-500 hover:text-gray-700 underline"
            >
              Выбрать другой файл
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <Upload className="w-10 h-10 text-gray-400 mx-auto" />
            <div>
              <p className="text-sm font-medium text-gray-700">
                Перетащите {fileType} файл сюда или
              </p>
              <button
                onClick={() => inputRef.current?.click()}
                className="text-primary-600 hover:text-primary-700 font-medium"
              >
                выберите файл
              </button>
            </div>
            <p className="text-xs text-gray-500">
              {isDocx ? 'Документ Word (.docx)' : 'Презентация PowerPoint (.pptx)'}
            </p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Оценка презентаций</h2>
        <p className="text-gray-600">Загрузите документ и презентацию для AI-оценки с потоковым выводом результатов</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Панель загрузки */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Upload className="w-5 h-5 mr-2" />
            Загрузка файлов
          </h3>

          <div className="space-y-6">
            {/* DOCX файл */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Документ (DOCX)
              </label>
              <FileUploadArea
                type="docx"
                file={docxFile}
                onFileSelect={(e) => handleFileSelect('docx', e)}
                onDrop={(e) => handleDrop('docx', e)}
                onDragOver={handleDragOver}
                inputRef={docxInputRef}
              />
              <input
                ref={docxInputRef}
                type="file"
                accept=".docx"
                onChange={(e) => handleFileSelect('docx', e)}
                className="hidden"
              />
            </div>

            {/* PPTX файл */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Презентация (PPTX)
              </label>
              <FileUploadArea
                type="pptx"
                file={pptxFile}
                onFileSelect={(e) => handleFileSelect('pptx', e)}
                onDrop={(e) => handleDrop('pptx', e)}
                onDragOver={handleDragOver}
                inputRef={pptxInputRef}
              />
              <input
                ref={pptxInputRef}
                type="file"
                accept=".pptx"
                onChange={(e) => handleFileSelect('pptx', e)}
                className="hidden"
              />
            </div>
          </div>

          {/* Настройки моделей */}
          <div className="mt-6 space-y-4">
            <h4 className="font-medium text-gray-900 flex items-center">
              <Settings className="w-4 h-4 mr-2" />
              Настройки моделей
            </h4>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Модель для анализа изображений
              </label>
              <select
                value={visionModel}
                onChange={(e) => setVisionModel(e.target.value)}
                className="input-field"
              >
                {availableModels.filter(model => model.includes('llava') || model.includes('vision')).map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Модель для оценки
              </label>
              <select
                value={evalModel}
                onChange={(e) => setEvalModel(e.target.value)}
                className="input-field"
              >
                {availableModels.filter(model => !model.includes('llava') && !model.includes('vision')).map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Кнопки */}
          <div className="mt-6 space-y-3">
            <button
              onClick={handleEvaluate}
              disabled={!docxFile || !pptxFile || isProcessing || !servicesStatus.aiJudge || !servicesStatus.ollama}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Оценка в процессе...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Начать оценку
                </>
              )}
            </button>

            <button
              onClick={resetForm}
              disabled={isProcessing}
              className="w-full btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Square className="w-4 h-4 mr-2 inline" />
              Сбросить
            </button>
          </div>
        </div>

        {/* Панель результатов */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Eye className="w-5 h-5 mr-2" />
              Результат оценки
            </h3>
            {streamingText && (
              <button
                onClick={downloadResult}
                className="btn-secondary flex items-center"
              >
                <Download className="w-4 h-4 mr-1" />
                Скачать
              </button>
            )}
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          <div
            ref={streamingRef}
            className="bg-gray-900 text-green-400 rounded-lg p-4 h-96 overflow-y-auto streaming-text"
          >
            {streamingText ? (
              <div className="whitespace-pre-wrap">
                {streamingText}
                {isProcessing && <span className="loading-dots">|</span>}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <Eye className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Результат оценки появится здесь</p>
                  <p className="text-sm mt-2">В режиме реального времени</p>
                </div>
              </div>
            )}
          </div>

          {isComplete && (
            <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-green-700 text-sm font-medium">
                ✅ Оценка завершена успешно!
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Результаты анализа */}
      {showResults && streamingText && (
        <div className="mt-8">
          <ResultsDisplay response={streamingText} />
        </div>
      )}
    </div>
  );
};

export default EvaluationTab;
