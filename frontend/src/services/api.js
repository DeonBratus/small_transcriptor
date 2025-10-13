import axios from 'axios';

// Конфигурация API
const TRANSCRIPTOR_API = 'http://localhost:8002';
const AI_JUDGE_API = 'http://localhost:8005';
const OLLAMA_API = 'http://212.8.228.176:9000';

// Создаем экземпляры axios с базовой конфигурацией
const transcriptorClient = axios.create({
  baseURL: TRANSCRIPTOR_API,
  timeout: 300000, // 5 минут для транскрибации
});

const aiJudgeClient = axios.create({
  baseURL: AI_JUDGE_API,
  timeout: 600000, // 10 минут для оценки
});

const ollamaClient = axios.create({
  baseURL: OLLAMA_API,
  timeout: 10000,
});

// Проверка статуса сервисов
export const checkServicesStatus = async () => {
  const status = {
    transcriptor: null,
    aiJudge: null,
    ollama: null
  };

  try {
    // Проверяем транскрибатор
    const transcriptorResponse = await transcriptorClient.get('/');
    status.transcriptor = transcriptorResponse.status === 200;
  } catch (error) {
    status.transcriptor = false;
  }

  try {
    // Проверяем AI Judge
    const aiJudgeResponse = await aiJudgeClient.get('/health/');
    status.aiJudge = aiJudgeResponse.status === 200;
  } catch (error) {
    status.aiJudge = false;
  }

  try {
    // Проверяем Ollama
    const ollamaResponse = await ollamaClient.get('/api/tags');
    status.ollama = ollamaResponse.status === 200;
  } catch (error) {
    status.ollama = false;
  }

  return status;
};

// API для транскрибации
export const transcribeAudio = async (file, numSpeakers = 4, useGpu = true) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('num_speakers', numSpeakers);
  formData.append('use_gpu', useGpu);

  const response = await transcriptorClient.post('/transcribe', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

// Потоковая транскрибация (эмуляция для Vosk)
export const streamTranscription = async (
  file, 
  numSpeakers = 4, 
  useGpu = true,
  onChunk = () => {},
  onComplete = () => {},
  onError = () => {}
) => {
  try {
    // Эмулируем потоковую транскрибацию для Vosk
    onChunk({ type: 'status', message: 'Начинаем транскрибацию...' });
    
    const result = await transcribeAudio(file, numSpeakers, useGpu);
    
    onChunk({ type: 'status', message: 'Транскрибация завершена, выполняется диаризация...' });
    
    // Эмулируем появление сегментов
    if (result.segments) {
      for (let i = 0; i < result.segments.length; i++) {
        const segment = result.segments[i];
        onChunk({ 
          type: 'segment', 
          ...segment,
          progress: `${i + 1}/${result.segments.length}`
        });
        
        // Небольшая задержка для эмуляции потоковости
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    
    onChunk({ type: 'final_segments', segments: result.segments });
    onComplete();
  } catch (error) {
    onError(error.message);
  }
};

export const downloadTranscription = async (file, numSpeakers = 4, useGpu = true) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('num_speakers', numSpeakers);
  formData.append('use_gpu', useGpu);

  const response = await transcriptorClient.post('/transcribe/download', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    responseType: 'blob',
  });

  return response.data;
};

// API для оценки презентаций
export const evaluatePresentation = async (
  docxFile, 
  pptxFile, 
  visionModel = 'llava', 
  evalModel = 'llama3.2'
) => {
  const formData = new FormData();
  formData.append('docx_file', docxFile);
  formData.append('pptx_file', pptxFile);
  formData.append('vision_model', visionModel);
  formData.append('eval_model', evalModel);

  const response = await aiJudgeClient.post('/evaluate/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

// Потоковая оценка презентаций
export const streamEvaluation = async (
  docxFile, 
  pptxFile, 
  visionModel = 'llava', 
  evalModel = 'llama3.2',
  onChunk = () => {},
  onComplete = () => {},
  onError = () => {}
) => {
  const formData = new FormData();
  formData.append('docx_file', docxFile);
  formData.append('pptx_file', pptxFile);
  formData.append('vision_model', visionModel);
  formData.append('eval_model', evalModel);

  try {
    const response = await fetch(`${AI_JUDGE_API}/evaluate/`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          
          if (data === '[DONE]') {
            onComplete();
            return;
          }
          
          if (data.startsWith('ERROR:')) {
            onError(data.slice(6));
            return;
          }
          
          onChunk(data);
        }
      }
    }
  } catch (error) {
    onError(error.message);
  }
};

// Получение доступных моделей Vosk (заглушка)
export const getAvailableWhisperModels = async () => {
  // Vosk использует предустановленные модели, возвращаем заглушку
  return [
    { name: 'vosk-model-ru-0.42', size: '1.8 GB', description: 'Русская модель Vosk (высокая точность)' },
    { name: 'vosk-model-small-ru-0.22', size: '45 MB', description: 'Компактная русская модель Vosk' }
  ];
};

// Получение доступных моделей Ollama
export const getAvailableModels = async () => {
  try {
    const response = await aiJudgeClient.get('/models/');
    return response.data.models || [];
  } catch (error) {
    console.error('Error fetching models:', error);
    return ['llama3.2', 'llava', 'mistral', 'phi3'];
  }
};

// Утилиты для работы с файлами
export const downloadFile = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const formatTime = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
