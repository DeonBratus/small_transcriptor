import json
import wave
import os
import tempfile
import urllib.request
import zipfile
from typing import List, Dict, Optional, Tuple
from pydub import AudioSegment
from vosk import Model, KaldiRecognizer
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import time
import math

class Transcriptor:
    """
    Упрощенный транскрибатор с Vosk и простой диаризацией
    """
    
    def __init__(self, model_path: str = "models/vosk-model-ru-0.42", 
                 is_advanced_segmentation=False, max_workers: Optional[int] = None):
        """
        Инициализация транскрибатора
        
        Args:
            model_path: Путь к модели Vosk
            is_advanced_segmentation: Использовать ли продвинутую сегментацию (отключено для упрощения)
            max_workers: Максимальное количество потоков для обработки (по умолчанию - количество CPU ядер)
        """
        self.model_path = model_path
        self.model = None
        self.is_advanced_segmentation = False  # Всегда используем простую диаризацию
        
        # Настройка многопоточности
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.model_lock = threading.Lock()  # Блокировка для безопасного доступа к модели
        
        print(f"Инициализация транскрибатора с {self.max_workers} потоками")
        
    
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
        """Загружает модель Vosk с поддержкой многопоточности"""
        with self.model_lock:
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
    
    def split_audio_into_chunks(self, audio_path: str, chunk_duration: float = 30.0) -> List[Tuple[str, float, float]]:
        """
        Разделяет аудиофайл на чанки для параллельной обработки
        
        Args:
            audio_path: Путь к аудиофайлу
            chunk_duration: Длительность чанка в секундах
            
        Returns:
            Список кортежей (путь_к_чанку, начало, конец)
        """
        print(f"Разделяем аудио на чанки по {chunk_duration} секунд...")
        
        # Получаем информацию о файле
        wf = wave.open(audio_path, 'rb')
        sample_rate = wf.getframerate()
        total_frames = wf.getnframes()
        total_duration = total_frames / sample_rate
        wf.close()
        
        chunks = []
        chunk_start = 0.0
        
        while chunk_start < total_duration:
            chunk_end = min(chunk_start + chunk_duration, total_duration)
            
            # Создаем временный файл для чанка
            temp_chunk = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_chunk.close()
            
            # Извлекаем чанк
            audio = AudioSegment.from_wav(audio_path)
            chunk_audio = audio[int(chunk_start * 1000):int(chunk_end * 1000)]
            chunk_audio.export(temp_chunk.name, format="wav")
            
            chunks.append((temp_chunk.name, chunk_start, chunk_end))
            chunk_start = chunk_end
        
        print(f"Создано {len(chunks)} чанков")
        return chunks
    
    def transcribe_chunk(self, chunk_info: Tuple[str, float, float]) -> List[Dict]:
        """
        Транскрибирует один чанк аудио
        
        Args:
            chunk_info: Кортеж (путь_к_чанку, начало, конец)
            
        Returns:
            Список результатов транскрипции с скорректированными временными метками
        """
        chunk_path, chunk_start, chunk_end = chunk_info
        
        try:
            # Загружаем модель в потоке
            self._load_model()
            
            wf = wave.open(chunk_path, 'rb')
            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(True)
            
            results = []
            
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
            
            # Корректируем временные метки относительно начала файла
            for result in results:
                if 'result' in result:
                    for word_info in result['result']:
                        word_info['start'] += chunk_start
                        word_info['end'] += chunk_start
            
            return results
            
        except Exception as e:
            print(f"Ошибка транскрипции чанка {chunk_path}: {e}")
            return []
        finally:
            # Удаляем временный файл чанка
            if os.path.exists(chunk_path):
                os.unlink(chunk_path)
    
    def transcribe_audio(self, audio_path: str, use_multithreading: bool = True, chunk_duration: float = 30.0) -> List[Dict]:
        """
        Транскрибация аудиофайла с использованием Vosk с поддержкой многопоточности
        
        Args:
            audio_path: Путь к аудиофайлу
            use_multithreading: Использовать ли многопоточность
            chunk_duration: Длительность чанка в секундах для многопоточности
        """
        if not use_multithreading or self.max_workers == 1:
            return self._transcribe_audio_single_thread(audio_path)
        
        print(f"Используем многопоточную обработку с {self.max_workers} потоками...")
        
        # Разделяем аудио на чанки
        chunks = self.split_audio_into_chunks(audio_path, chunk_duration)
        
        if len(chunks) == 1:
            print("Файл слишком короткий для многопоточности, используем однопоточную обработку")
            return self._transcribe_audio_single_thread(audio_path)
        
        # Обрабатываем чанки параллельно
        all_results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Запускаем задачи
            future_to_chunk = {executor.submit(self.transcribe_chunk, chunk): chunk for chunk in chunks}
            
            # Собираем результаты по мере готовности
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result()
                    all_results.extend(chunk_results)
                    print(f"Обработан чанк {chunk[1]:.1f}-{chunk[2]:.1f}с")
                except Exception as e:
                    print(f"Ошибка обработки чанка {chunk[1]:.1f}-{chunk[2]:.1f}с: {e}")
        
        processing_time = time.time() - start_time
        print(f"Многопоточное распознавание завершено за {processing_time:.2f}с. Получено {len(all_results)} сегментов.")
        
        return all_results
    
    def _transcribe_audio_single_thread(self, audio_path: str) -> List[Dict]:
        """
        Однопоточная транскрибация аудиофайла (оригинальный метод)
        """
        self._load_model()
        
        wf = wave.open(audio_path, 'rb')
        
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            print("Предупреждение: аудио не в идеальном формате")

        rec = KaldiRecognizer(self.model, wf.getframerate())
        rec.SetWords(True)

        results = []
        print("Идет распознавание речи (однопоточный режим)...")

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
                                    num_speakers: int = 4,
                                    use_multithreading: bool = True,
                                    chunk_duration: float = 30.0) -> Optional[List[Dict]]:
        """
        Основной метод транскрибации MP3 файла с разделением на спикеров и поддержкой многопоточности
        
        Args:
            mp3_path: Путь к MP3 файлу
            num_speakers: Количество спикеров
            use_multithreading: Использовать ли многопоточность
            chunk_duration: Длительность чанка в секундах для многопоточности
        """
        print(f"Начинаем обработку файла: {mp3_path}")
        print(f"Количество спикеров: {num_speakers}")
        print(f"Многопоточность: {'Включена' if use_multithreading else 'Отключена'}")
        if use_multithreading:
            print(f"Размер чанка: {chunk_duration} секунд")

        # Конвертируем MP3 в WAV
        wav_path = self.convert_mp3_to_wav(mp3_path)
        if not wav_path:
            print("Ошибка конвертации MP3 в WAV!")
            return None

        try:
            # Транскрибация с многопоточностью
            results = self.transcribe_audio(wav_path, use_multithreading, chunk_duration)
            
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