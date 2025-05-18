from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pytube import YouTube
from pydantic import BaseModel  # Для определения моделей данных
from typing import List, Dict, Any  # Для типизации


# --- Модели данных (для валидации и документации API) ---
class VideoFormatInfo(BaseModel):
    itag: str
    resolution: str | None  # Может быть None для аудио
    mime_type: str | None
    filesize: int
    abr: str | None  # Для аудио - average bitrate


class VideoDetails(BaseModel):
    title: str
    thumbnail_url: str
    duration: int  # в секундах
    available_formats: List[VideoFormatInfo]


class DownloadLink(BaseModel):
    download_url: str
    filename: str


# --- Инициализация FastAPI приложения ---
app = FastAPI(
    title="YouTube Downloader API",
    description="Простой API для получения информации и ссылок на скачивание видео с YouTube",
    version="1.0.0"
)

# --- Настройка CORS ---
# Это важно, чтобы ваш React-фронтенд мог обращаться к этому API
origins = [
    "http://localhost:3000",  # Адрес вашего локального React-сервера разработки
    # Добавьте сюда URL вашего продакшн фронтенда, если он есть
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы (GET, POST, и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)


# --- API Эндпоинты ---

@app.get("/api/video-info", response_model=VideoDetails)
async def get_video_information(url: str):
    """
    Получает информацию о YouTube видео по его URL.
    Возвращает название, URL превью, длительность и список доступных форматов.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL параметр не может быть пустым.")
    try:
        yt = YouTube(url)

        formats_info: List[VideoFormatInfo] = []
        # progressive=True означает, что видео и аудио в одном файле
        # file_extension='mp4' чтобы получить только mp4 форматы
        for stream in yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc():
            formats_info.append(VideoFormatInfo(
                itag=str(stream.itag),
                resolution=stream.resolution,
                mime_type=stream.mime_type,
                filesize=stream.filesize,
                abr=stream.abr
            ))

        # Если нет progressive mp4, можно добавить и другие (например, только аудио или адаптивные)
        # или вернуть ошибку, если нет подходящих форматов

        if not formats_info:
            raise HTTPException(status_code=404, detail="Подходящие форматы MP4 не найдены для этого видео.")

        return VideoDetails(
            title=yt.title,
            thumbnail_url=yt.thumbnail_url,
            duration=yt.length,
            available_formats=formats_info
        )
    except Exception as e:
        # Логирование ошибки было бы здесь полезно в продакшене
        print(f"Ошибка при получении информации о видео: {e}")  # Для отладки
        raise HTTPException(status_code=500, detail=f"Ошибка сервера при обработке URL: {str(e)}")


@app.get("/api/download-link", response_model=DownloadLink)
async def get_download_link(url: str, itag: str):
    """
    Получает прямую ссылку на скачивание видео по URL и выбранному itag (качеству/формату).
    """
    if not url or not itag:
        raise HTTPException(status_code=400, detail="Параметры 'url' и 'itag' не могут быть пустыми.")
    try:
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(int(itag))

        if not stream:
            raise HTTPException(status_code=404, detail=f"Формат с itag '{itag}' не найден для этого видео.")

        # pytube предоставляет stream.url, которая является прямой (часто временной) ссылкой
        return DownloadLink(
            download_url=stream.url,
            filename=f"{yt.title.replace(' ', '_')}_{stream.resolution or stream.abr}.{stream.subtype}"
        )
    except Exception as e:
        print(f"Ошибка при получении ссылки на скачивание: {e}")  # Для отладки
        raise HTTPException(status_code=500, detail=f"Ошибка сервера при получении ссылки: {str(e)}")


# --- Запуск сервера (для локальной разработки) ---
if __name__ == "__main__":
    import uvicorn

    # host="0.0.0.0" делает сервер доступным из вашей локальной сети
    uvicorn.run(app, host="0.0.0.0", port=8000)