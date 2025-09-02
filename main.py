import os 
from transcriptor import Transcriptor
# Функция для примера использования
def main():
    """Пример использования класса транскрибатора"""
    # Укажите путь к вашему MP3 файлу
    mp3_file = "32140-312ds213-91094-2134.mp3"

    if not os.path.exists(mp3_file):
        print(f"Файл {mp3_file} не найден!")
        print("Убедитесь, что файл существует в той же папке")
        return

    # Создаем экземпляр транскрибатора
    transcriber = Transcriptor()
    
    # Запуск транскрибации
    transcription = transcriber.transcribe_mp3_with_speakers(mp3_file, num_speakers=4)

    if transcription:
        # Вывод результатов
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТЫ ТРАНСКРИБАЦИИ:")
        print("="*60)

        for segment in transcription:
            print(f"[{segment['speaker']}] {segment['text']}")
            print(f"Время: {transcriber.format_time(segment['start'])} - {transcriber.format_time(segment['end'])}\n")

        # Сохранение в файл
        transcriber.save_results(transcription, "transcription_result.txt")

        print("Обработка завершена успешно!")


if __name__ == "__main__":
    main()