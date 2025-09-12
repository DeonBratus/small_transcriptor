import json
import wave
import os
import tempfile
import urllib.request
import zipfile
from typing import List, Dict, Optional
from pydub import AudioSegment
import torch
from pyannote.audio import Pipeline
from vosk import Model, KaldiRecognizer

class Transcriptor:
    """
    Класс для транскрибации MP3 файлов с разделением по спикерам и поддержкой GPU
    """
    
    def __init__(self, model_path: str = "models/vosk-model-ru-0.42", use_gpu: bool = True, is_advanced_segmentation=False):
        """
        Инициализация транскрибатора
        
        Args:
            model_path: Путь к модели Vosk
            use_gpu: Использовать ли GPU для обработки
        """
        self.model_path = model_path
        self.model = None
        self.use_gpu = use_gpu
        self.speaker_pipeline = None
        self.device = torch.device("cuda" if use_gpu and torch.cuda.is_available() else "cpu")
        self.is_advanced_segmentation = False
        
        print(f"Используемое устройство: {self.device}")
        
    def set_use_gpu(self, use_gpu: bool):
        """Изменение режима использования GPU"""
        self.use_gpu = use_gpu
        self.device = torch.device("cuda" if use_gpu and torch.cuda.is_available() else "cpu")
        print(f"Устройство изменено на: {self.device}")
    
    def _download_model(self) -> None:
        """Скачивает и распаковывает модель Vosk если она отсутствует"""
        if not os.path.exists(self.model_path):
            print("Модель Vosk не найдена. Скачиваем...")
            
            model_url = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
            zip_path = "models/vosk-model-ru-0.42.zip"

            urllib.request.urlretrieve(model_url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".")
            os.remove(zip_path)
            print("Модель Vosk скачана и распакована")
    
    def _load_model(self) -> None:
        """Загружает модель Vosk"""
        if self.model is None:
            self._download_model()
            self.model = Model(self.model_path)
    
    def _load_speaker_pipeline(self):
        """Загружает pipeline для разделения спикеров"""
        if self.speaker_pipeline is None:
            try:
                # PyAnnote для диаризации (разделения спикеров)
                self.speaker_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=False
                )
                if self.use_gpu and torch.cuda.is_available():
                    self.speaker_pipeline = self.speaker_pipeline.to(self.device)
                print("Модель разделения спикеров загружена")
            except Exception as e:
                print(f"Ошибка загрузки модели спикеров: {e}. Используем простой метод.")
                self.speaker_pipeline = None
    
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
        print("Идет распознавание...")

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
        return results
    
    def advanced_speaker_segmentation(self, audio_path: str, transcription_results: List[Dict]) -> List[Dict]:
        """
        Продвинутое разделение на спикеров с использованием pyannote
        """
        try:
            self._load_speaker_pipeline()
            
            if self.speaker_pipeline is None:
                return self.simple_speaker_segmentation(transcription_results)
            
            # Диаризация спикеров
            diarization = self.speaker_pipeline(audio_path)
            
            segments = []
            for result in transcription_results:
                if 'result' not in result:
                    continue

                for word_info in result['result']:
                    start = word_info['start']
                    end = word_info['end']
                    word = word_info['word']
                    
                    # Находим спикера для этого временного отрезка
                    speaker = "SPEAKER_00"
                    for turn, _, speaker_id in diarization.itertracks(yield_label=True):
                        if turn.start <= start <= turn.end:
                            speaker = str(speaker_id)
                            break
                    
                    segments.append({
                        'start': start,
                        'end': end,
                        'text': word,
                        'speaker': speaker
                    })
            
            return segments
            
        except Exception as e:
            print(f"Ошибка продвинутой диаризации: {e}. Используем простой метод.")
            return self.simple_speaker_segmentation(transcription_results)
    
    def simple_speaker_segmentation(self, transcription_results: List[Dict], 
                                   num_speakers: int = 4) -> List[Dict]:
        """
        Простое разделение на спикеров по паузам
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
        """
        grouped = []
        current_group = None

        for segment in segments:
            if current_group is None:
                current_group = segment.copy()
                current_group['text'] = segment['text']
            elif (current_group['speaker'] == segment['speaker'] and
                  segment['start'] - current_group['end'] < time_threshold):
                current_group['text'] += " " + segment['text']
                current_group['end'] = segment['end']
            else:
                grouped.append(current_group)
                current_group = segment.copy()
                current_group['text'] = segment['text']

        if current_group:
            grouped.append(current_group)

        return grouped
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """
        Форматирование времени
        """
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"
    
    def save_results(self, segments: List[Dict], output_file: str = "transcription.txt") -> None:
        """
        Сохранение результатов транскрибации
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
        """
        print("Начинаем обработку MP3 файла...")

        wav_path = self.convert_mp3_to_wav(mp3_path)

        if not wav_path:
            print("Ошибка конвертации!")
            return None

        try:
            results = self.transcribe_audio(wav_path)
            
            # Используем продвинутое разделение спикеров если доступно
            if self.speaker_pipeline and self.is_advanced_segmentation:
                segments = self.advanced_speaker_segmentation(wav_path, results)
            else:
                segments = self.simple_speaker_segmentation(results, num_speakers)

            grouped_segments = self.group_segments_by_speaker(segments)

            return grouped_segments

        except Exception as e:
            print(f"Ошибка транскрибации: {e}")
            return None
        finally:
            if os.path.exists(wav_path):
                os.unlink(wav_path)
                print("Временный файл удален")