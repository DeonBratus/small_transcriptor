import React, { useState, useRef, useEffect } from 'react';
import { Upload, Mic, Download, Settings, Play } from 'lucide-react';
import { transcribeAudio, downloadTranscription, streamTranscription, getAvailableWhisperModels, formatTime, formatFileSize } from '../services/api';
import './TranscriptionTab.css';

const TranscriptionTab = ({ servicesStatus }) => {
  const [file, setFile] = useState(null);
  const [numSpeakers, setNumSpeakers] = useState(4);
  const [useGpu, setUseGpu] = useState(true);
  const [availableModels, setAvailableModels] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [processingTime, setProcessingTime] = useState(null);
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingProgress, setStreamingProgress] = useState('');
  const fileInputRef = useRef(null);
  const streamingRef = useRef(null);

  // Загружаем доступные модели при монтировании компонента
  useEffect(() => {
    const loadData = async () => {
      try {
        const models = await getAvailableWhisperModels();
        setAvailableModels(models);
      } catch (error) {
        console.error('Error loading models:', error);
      }
    };
    loadData();
  }, []);

  // Автопрокрутка при потоковом выводе
  useEffect(() => {
    if (streamingRef.current) {
      streamingRef.current.scrollTop = streamingRef.current.scrollHeight;
    }
  }, [streamingText]);

  const handleFileSelect = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
      setResult(null);
      setStreamingText('');
    }
  };


  const handleDrop = (event) => {
    event.preventDefault();
    const droppedFile = event.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith('audio/')) {
      setFile(droppedFile);
      setError(null);
      setResult(null);
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const handleTranscribe = async () => {
    if (!file) {
      setError('Пожалуйста, выберите аудио файл');
      return;
    }

    if (!servicesStatus.transcriptor) {
      setError('Сервис транскрибации недоступен');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResult(null);
    setStreamingText('');

    try {
      const startTime = Date.now();
      const response = await transcribeAudio(file, numSpeakers, useGpu);
      const endTime = Date.now();
      
      setResult(response);
      setProcessingTime((endTime - startTime) / 1000);
    } catch (error) {
      setError(error.response?.data?.detail || error.message || 'Ошибка транскрибации');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleStreamTranscribe = async () => {
    if (!file) {
      setError('Пожалуйста, выберите аудио файл');
      return;
    }

    if (!servicesStatus.transcriptor) {
      setError('Сервис транскрибации недоступен');
      return;
    }

    setIsStreaming(true);
    setError(null);
    setResult(null);
    setStreamingText('');
    setStreamingProgress('');

    try {
      await streamTranscription(
        file,
        numSpeakers,
        useGpu,
        (chunk) => {
          if (chunk.type === 'status') {
            setStreamingText(prev => prev + `[СТАТУС] ${chunk.message}\n`);
            setStreamingProgress(chunk.message);
          } else if (chunk.type === 'segment') {
            setStreamingText(prev => prev + `[${chunk.start?.toFixed(2)}s] ${chunk.text} (${chunk.progress})\n`);
            setStreamingProgress(`Обработано: ${chunk.progress}`);
          } else if (chunk.type === 'final_segments' && chunk.segments) {
            setResult({ segments: chunk.segments });
            setStreamingText(prev => prev + `[ЗАВЕРШЕНО] Получено ${chunk.segments.length} сегментов с диаризацией\n`);
            setStreamingProgress('Диаризация завершена!');
          } else if (chunk.text) {
            // Fallback для старых форматов
            setStreamingText(prev => prev + `[${chunk.start?.toFixed(2)}s] ${chunk.text}\n`);
          }
        },
        () => {
          setIsStreaming(false);
          setStreamingText(prev => prev + `[ЗАВЕРШЕНО] Потоковая транскрибация завершена!\n`);
        },
        (error) => {
          setError(error);
          setIsStreaming(false);
          setStreamingText(prev => prev + `[ОШИБКА] ${error}\n`);
        }
      );
    } catch (error) {
      setError(error.message || 'Ошибка потоковой транскрибации');
      setIsStreaming(false);
      setStreamingText(prev => prev + `[ОШИБКА] ${error.message}\n`);
    }
  };

  const handleDownload = async () => {
    if (!file) return;

    try {
      const blob = await downloadTranscription(file, numSpeakers, useGpu);
      const filename = `transcription_${file.name.replace(/\.[^/.]+$/, '')}.txt`;
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setError('Ошибка при скачивании файла');
    }
  };

  const resetForm = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setProcessingTime(null);
    setStreamingText('');
    setIsStreaming(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Транскрибация аудио с Vosk</h2>
        <p className="text-gray-600">Загрузите аудио файл для автоматической транскрибации с разделением по спикерам с использованием Vosk</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Панель загрузки */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Upload className="w-5 h-5 mr-2" />
            Загрузка файла
          </h3>

          {/* Область загрузки */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              file
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            {file ? (
              <div className="space-y-2">
                <Mic className="w-12 h-12 text-green-500 mx-auto" />
                <p className="text-sm font-medium text-green-700">{file.name}</p>
                <p className="text-xs text-green-600">{formatFileSize(file.size)}</p>
                <button
                  onClick={resetForm}
                  className="text-xs text-gray-500 hover:text-gray-700 underline"
                >
                  Выбрать другой файл
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <Upload className="w-12 h-12 text-gray-400 mx-auto" />
                <div>
                  <p className="text-sm font-medium text-gray-700">
                    Перетащите аудио файл сюда или
                  </p>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="text-primary-600 hover:text-primary-700 font-medium"
                  >
                    выберите файл
                  </button>
                </div>
                <p className="text-xs text-gray-500">
                  Поддерживаются форматы: MP3, WAV, OGG
                </p>
              </div>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*"
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* Настройки */}
          <div className="mt-6 space-y-4">
            <h4 className="font-medium text-gray-900 flex items-center">
              <Settings className="w-4 h-4 mr-2" />
              Настройки
            </h4>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Доступные модели Vosk
              </label>
              <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                {availableModels.map(model => (
                  <div key={model.name} className="mb-1">
                    <strong>{model.name}</strong> ({model.size}) - {model.description}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Количество спикеров: {numSpeakers}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={numSpeakers}
                onChange={(e) => setNumSpeakers(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="useGpu"
                checked={useGpu}
                onChange={(e) => setUseGpu(e.target.checked)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label htmlFor="useGpu" className="ml-2 block text-sm text-gray-700">
                Использовать GPU (рекомендуется)
              </label>
            </div>
          </div>


          {/* Кнопки обработки */}
          <div className="mt-6 space-y-3">
            <button
              onClick={handleTranscribe}
              disabled={!file || isProcessing || isStreaming || !servicesStatus.transcriptor}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Обработка...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Обычная транскрибация
                </>
              )}
            </button>

            <button
              onClick={handleStreamTranscribe}
              disabled={!file || isProcessing || isStreaming || !servicesStatus.transcriptor}
              className="w-full btn-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isStreaming ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                  Потоковая обработка...
                </>
              ) : (
                <>
                  <Mic className="w-4 h-4 mr-2" />
                  Потоковая транскрибация
                </>
              )}
            </button>
          </div>
        </div>

        {/* Панель результатов */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Mic className="w-5 h-5 mr-2" />
            Результат
          </h3>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {processingTime && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <p className="text-blue-700 text-sm">
                Время обработки: {processingTime.toFixed(2)} сек
              </p>
            </div>
          )}

          {/* Потоковый вывод */}
          {streamingText && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-700">Live транскрибация:</h4>
                {isStreaming && (
                  <div className="flex items-center text-sm text-blue-600">
                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-2"></div>
                    {streamingProgress || 'Обработка...'}
                  </div>
                )}
              </div>
              <div
                ref={streamingRef}
                className="bg-gray-900 text-green-400 rounded-lg p-4 h-64 overflow-y-auto streaming-text font-mono text-sm"
              >
                <div className="whitespace-pre-wrap">
                  {streamingText}
                  {isStreaming && <span className="animate-pulse">|</span>}
                </div>
              </div>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                <div className="space-y-3">
                  {result.segments?.map((segment, index) => (
                    <div key={index} className="border-l-4 border-primary-500 pl-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-primary-600">
                          {segment.speaker}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatTime(segment.start)} - {formatTime(segment.end)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700">{segment.text}</p>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={handleDownload}
                className="w-full btn-secondary flex items-center justify-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Скачать результат
              </button>
            </div>
          )}

          {!result && !error && !isProcessing && (
            <div className="text-center py-12 text-gray-500">
              <Mic className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Результат транскрибации появится здесь</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TranscriptionTab;
