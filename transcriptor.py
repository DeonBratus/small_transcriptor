import json
from vosk import Model, KaldiRecognizer
import wave
import os
from pydub import AudioSegment
from collections import defaultdict
import tempfile
import urllib.request
import zipfile
from typing import List, Dict, Optional


class Transcriptor:
    """
    Класс для транскрибации MP3 файлов с разделением по спикерам
    """
    
    def __init__(self, model_path: str = "vosk-model-ru-0.42"):
        """
        Инициализация транскрибатора
        
        Args:
            model_path: Путь к модели Vosk
        """
        self.model_path = model_path
        self.model = None
        
    def _download_model(self) -> None:
        """Скачивает и распаковывает модель Vosk если она отсутствует"""
        if not os.path.exists(self.model_path):
            print("Модель не найдена. Скачиваем...")
            
            model_url = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
            zip_path = "vosk-model-ru-0.42.zip"

            urllib.request.urlretrieve(model_url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".")
            os.remove(zip_path)
            print("Модель скачана и распакована")
    
    def _load_model(self) -> None:
        """Загружает модель Vosk"""
        if self.model is None:
            self._download_model()
            self.model = Model(self.model_path)
    
    def convert_mp3_to_wav(self, mp3_path: str, sample_rate: int = 16000) -> Optional[str]:
        """
        Конвертирует MP3 в WAV формат для Vosk
        
        Args:
            mp3_path: Путь к MP3 файлу
            sample_rate: Частота дискретизации
            
        Returns:
            Путь к временному WAV файлу или None при ошибке
        """
        print(f"Конвертируем {mp3_path} в WAV...")

        # Создаем временный файл
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav.close()

        try:
            # Загружаем MP3
            audio = AudioSegment.from_mp3(mp3_path)

            # Конвертируем в нужный формат
            audio = audio.set_channels(1)          # mono
            audio = audio.set_frame_rate(sample_rate)  # 16kHz
            audio = audio.set_sample_width(2)      # 16-bit PCM

            # Сохраняем
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
        
        Args:
            audio_path: Путь к WAV файлу
            
        Returns:
            Список результатов распознавания
        """
        self._load_model()
        
        # Открываем аудиофайл
        wf = wave.open(audio_path, 'rb')

        # Проверяем формат аудио
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print("Предупреждение: аудио не в идеальном формате, но попробуем обработать...")

        # Создаем распознаватель
        rec = KaldiRecognizer(self.model, wf.getframerate())
        rec.SetWords(True)

        # Читаем и обрабатываем аудио
        results = []
        print("Идет распознавание...")

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                results.append(result)

        # Финальный результат
        final_result = json.loads(rec.FinalResult())
        results.append(final_result)

        wf.close()
        return results
    
    @staticmethod
    def simple_speaker_segmentation(transcription_results: List[Dict], 
                                   num_speakers: int = 4) -> List[Dict]:
        """
        Простое разделение на спикеров по паузам
        
        Args:
            transcription_results: Результаты транскрибации
            num_speakers: Количество спикеров
            
        Returns:
            Сегменты с указанием спикера
        """
        segments = []
        current_speaker = 0
        last_end_time = 0

        for result in transcription_results:
            if 'result' not in result:
                continue

            for word_info in result['result']:
                start = word_info['start']
                end = word_info['end']
                word = word_info['word']

                # Если пауза больше 1.5 секунды - меняем спикера
                if start - last_end_time > 1.5:
                    current_speaker = (current_speaker + 1) % num_speakers

                segments.append({
                    'start': start,
                    'end': end,
                    'text': word,
                    'speaker': f"SPEAKER_{current_speaker:02d}"
                })
                last_end_time = end

        return segments
    
    @staticmethod
    def group_segments_by_speaker(segments: List[Dict], 
                                 time_threshold: float = 2.0) -> List[Dict]:
        """
        Группировка сегментов по спикерам
        
        Args:
            segments: Сегменты транскрибации
            time_threshold: Порог для объединения сегментов
            
        Returns:
            Сгруппированные сегменты
        """
        grouped = []
        current_group = None

        for segment in segments:
            if current_group is None:
                current_group = {
                    'speaker': segment['speaker'],
                    'text': segment['text'],
                    'start': segment['start'],
                    'end': segment['end']
                }
            elif (current_group['speaker'] == segment['speaker'] and
                  segment['start'] - current_group['end'] < time_threshold):
                current_group['text'] += " " + segment['text']
                current_group['end'] = segment['end']
            else:
                grouped.append(current_group)
                current_group = {
                    'speaker': segment['speaker'],
                    'text': segment['text'],
                    'start': segment['start'],
                    'end': segment['end']
                }

        if current_group:
            grouped.append(current_group)

        return grouped
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """
        Форматирование времени
        
        Args:
            seconds: Время в секундах
            
        Returns:
            Отформатированная строка времени
        """
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"
    
    def save_results(self, segments: List[Dict], output_file: str = "transcription.txt") -> None:
        """
        Сохранение результатов транскрибации
        
        Args:
            segments: Сегменты транскрибации
            output_file: Путь для сохранения результатов
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            for segment in segments:
                f.write(f"[{segment['speaker']}] ")
                f.write(f"{self.format_time(segment['start'])}-{self.format_time(segment['end'])}\n")
                f.write(f"{segment['text']}\n")
                f.write("-" * 50 + "\n\n")

        print(f"Результаты сохранены в {output_file}")
    
    def transcribe_mp3_with_speakers(self, mp3_path: str, 
                                    num_speakers: int = 4) -> Optional[List[Dict]]:
        """
        Транскрибация MP3 файла с разделением на спикеров
        
        Args:
            mp3_path: Путь к MP3 файлу
            num_speakers: Количество спикеров
            
        Returns:
            Результаты транскрибации или None при ошибке
        """
        print("Начинаем обработку MP3 файла...")

        # Конвертируем MP3 в WAV
        wav_path = self.convert_mp3_to_wav(mp3_path)

        if not wav_path:
            print("Ошибка конвертации!")
            return None

        try:
            # Транскрибация
            results = self.transcribe_audio(wav_path)

            # Простое разделение на спикеров
            segments = self.simple_speaker_segmentation(results, num_speakers)

            # Группируем результаты
            grouped_segments = self.group_segments_by_speaker(segments)

            return grouped_segments

        finally:
            # Удаляем временный WAV файл
            if os.path.exists(wav_path):
                os.unlink(wav_path)
                print("Временный файл удален")

