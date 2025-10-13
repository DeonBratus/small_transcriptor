import json
import wave
import os
import tempfile
import urllib.request
import zipfile
from typing import List, Dict, Optional
from pydub import AudioSegment
import torch
from vosk import Model, KaldiRecognizer

class Transcriptor:
    """
    Упрощенный транскрибатор с Vosk и простой диаризацией
    """
    
    def __init__(self, model_path: str = "models/vosk-model-ru-0.42", use_gpu: bool = True, is_advanced_segmentation=False):
        """
        Инициализация транскрибатора
        
        Args:
            model_path: Путь к модели Vosk
            use_gpu: Использовать ли GPU для обработки (для совместимости, Vosk работает только на CPU)
            is_advanced_segmentation: Использовать ли продвинутую сегментацию (отключено для упрощения)
        """
        self.model_path = model_path
        self.model = None
        self.use_gpu = use_gpu  # Сохраняем для совместимости с API
        self.is_advanced_segmentation = False  # Всегда используем простую диаризацию
        
        # Проверяем доступность GPU для информационных целей
        if use_gpu and torch.cuda.is_available():
            print(f"GPU доступен: {torch.cuda.get_device_name(0)}")
            print("Примечание: Vosk работает только на CPU, GPU используется для других операций")
        else:
            print("Используется CPU для всех операций")
        
    def set_use_gpu(self, use_gpu: bool):
        """Изменение режима использования GPU (для совместимости с API)"""
        self.use_gpu = use_gpu
        if use_gpu and torch.cuda.is_available():
            print(f"GPU режим включен: {torch.cuda.get_device_name(0)}")
        else:
            print("Используется CPU режим")
    
    def _download_model(self) -> None:
        """Скачивает и распаковывает модель Vosk если она отсутствует"""
        if not os.path.exists(self.model_path):
            print("Модель Vosk не найдена. Скачиваем...")
            
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            model_url = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
            zip_path = "models/vosk-model-ru-0.42.zip"

            urllib.request.urlretrieve(model_url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("models/")
            os.remove(zip_path)
            print("Модель Vosk скачана и распакована")
    
    def _load_model(self) -> None:
        """Загружает модель Vosk"""
        if self.model is None:
            self._download_model()
            print(f"Загружаем модель Vosk из {self.model_path}...")
            self.model = Model(self.model_path)
            print("Модель Vosk загружена успешно")
    
    def convert_mp3_to_wav(self, mp3_path: str, sample_rate: int = 16000) -> Optional[str]:
        """
        Конвертирует MP3 в WAV формат для Vosk
        """
        print(f"Конвертируем {mp3_path} в WAV...")

        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav.close()

        try:
            audio = AudioSegment.from_file(mp3_path)
            audio = audio.set_channels(1).set_frame_rate(sample_rate).set_sample_width(2)
            audio.export(temp_wav.name, format="wav")
            print("Конвертация завершена")
            return temp_wav.name

        except Exception as e:
            print(f"Ошибка конвертации: {e}")
            os.unlink(temp_wav.name)
            return None
    
    def transcribe_audio(self, audio_path: str) -> List[Dict]:
        """
        Транскрибация аудиофайла с использованием Vosk
        """
        self._load_model()
        
        wf = wave.open(audio_path, 'rb')
        
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            print("Предупреждение: аудио не в идеальном формате")

        rec = KaldiRecognizer(self.model, wf.getframerate())
        rec.SetWords(True)

        results = []
        print("Идет распознавание речи...")

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                results.append(result)

        final_result = json.loads(rec.FinalResult())
        results.append(final_result)

        wf.close()
        print(f"Распознавание завершено. Получено {len(results)} сегментов.")
        return results
    
    def simple_speaker_segmentation(self, transcription_results: List[Dict], 
                                   num_speakers: int = 4) -> List[Dict]:
        """
        Упрощенное разделение на спикеров по паузам и длине сегментов
        """
        print(f"Выполняем диаризацию для {num_speakers} спикеров...")
        
        segments = []
        current_speaker = 0
        last_end_time = 0
        speaker_change_threshold = 2.0  # Пауза в секундах для смены спикера

        for result in transcription_results:
            if 'result' not in result:
                continue

            for word_info in result['result']:
                start = word_info['start']
                end = word_info['end']
                word = word_info['word']

                # Смена спикера при длинной паузе
                if start - last_end_time > speaker_change_threshold:
                    current_speaker = (current_speaker + 1) % num_speakers

                segments.append({
                    'start': start,
                    'end': end,
                    'text': word,
                    'speaker': f"SPEAKER_{current_speaker:02d}"
                })
                last_end_time = end

        print(f"Диаризация завершена. Получено {len(segments)} словесных сегментов.")
        return segments
    
    @staticmethod
    def group_segments_by_speaker(segments: List[Dict], 
                                 time_threshold: float = 3.0) -> List[Dict]:
        """
        Группировка сегментов по спикерам с объединением близких по времени фраз
        """
        if not segments:
            return []
            
        grouped = []
        current_group = None

        for segment in segments:
            if current_group is None:
                current_group = segment.copy()
                current_group['text'] = segment['text']
            elif (current_group['speaker'] == segment['speaker'] and
                  segment['start'] - current_group['end'] < time_threshold):
                # Объединяем с предыдущим сегментом того же спикера
                current_group['text'] += " " + segment['text']
                current_group['end'] = segment['end']
            else:
                # Начинаем новый сегмент
                grouped.append(current_group)
                current_group = segment.copy()
                current_group['text'] = segment['text']

        if current_group:
            grouped.append(current_group)

        print(f"Группировка завершена. Получено {len(grouped)} речевых сегментов.")
        return grouped
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """
        Форматирование времени в читаемый вид
        """
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"
    
    def save_results(self, segments: List[Dict], output_file: str = "transcription.txt") -> None:
        """
        Сохранение результатов транскрибации в файл
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Результаты транскрибации\n")
            f.write("=" * 50 + "\n\n")
            
            for segment in segments:
                f.write(f"[{segment['speaker']}] ")
                f.write(f"{self.format_time(segment['start'])}-{self.format_time(segment['end'])}\n")
                f.write(f"{segment['text']}\n")
                f.write("-" * 50 + "\n\n")

        print(f"Результаты сохранены в {output_file}")
    
    def transcribe_mp3_with_speakers(self, mp3_path: str, 
                                    num_speakers: int = 4) -> Optional[List[Dict]]:
        """
        Основной метод транскрибации MP3 файла с разделением на спикеров
        """
        print(f"Начинаем обработку файла: {mp3_path}")
        print(f"Количество спикеров: {num_speakers}")

        # Конвертируем MP3 в WAV
        wav_path = self.convert_mp3_to_wav(mp3_path)
        if not wav_path:
            print("Ошибка конвертации MP3 в WAV!")
            return None

        try:
            # Транскрибация
            results = self.transcribe_audio(wav_path)
            
            # Простая диаризация
            segments = self.simple_speaker_segmentation(results, num_speakers)

            # Группировка сегментов
            grouped_segments = self.group_segments_by_speaker(segments)

            print(f"Обработка завершена успешно. Получено {len(grouped_segments)} речевых сегментов.")
            return grouped_segments

        except Exception as e:
            print(f"Ошибка транскрибации: {e}")
            return None
        finally:
            # Очищаем временный файл
            if os.path.exists(wav_path):
                os.unlink(wav_path)
                print("Временный WAV файл удален")