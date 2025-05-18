import logging
import asyncio
import threading
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import yt_dlp
import os  # Для определения пути к cookies

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Путь к файлу cookies ---
# Определяем абсолютный путь к файлу cookies.txt, который должен лежать рядом с main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE_PATH = os.path.join(BASE_DIR, "cookies.txt")

logger.info(f"Попытка использовать cookies из файла: {COOKIES_FILE_PATH}")
if not os.path.exists(COOKIES_FILE_PATH):
    logger.warning(f"Файл cookies не найден по пути: {COOKIES_FILE_PATH}. Запросы могут быть ограничены YouTube.")


# --- Модели данных Pydantic ---
class VideoFormatInfo(BaseModel):
    itag: str
    resolution: Optional[str] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    ext: str
    filesize: Optional[int] = None
    format_note: Optional[str] = None
    fps: Optional[int] = None
    abr: Optional[float] = None  # Average audio bitrate
    tbr: Optional[float] = None  # Total bitrate


class VideoDetails(BaseModel):
    title: str
    thumbnail_url: str
    duration: int  # в секундах
    uploader: Optional[str] = None
    description: Optional[str] = None
    available_formats: List[VideoFormatInfo]


class DownloadResponse(BaseModel):
    message: str
    direct_download_url: Optional[str] = None
    filename: Optional[str] = None


# --- Инициализация FastAPI ---
app = FastAPI(
    title="YouTube Downloader API with yt-dlp",
    description="API для получения информации и прямых ссылок на скачивание видео с YouTube с использованием yt-dlp.",
    version="1.1.0"
)

origins = [
    "http://localhost:3000",  # Для локальной разработки React
    # "*" # Можно разрешить все источники, если API публичный, но это менее безопасно
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Вспомогательные функции, работающие с yt-dlp ---

def fetch_video_info_blocking(video_url: str) -> Dict[str, Any]:
    """
    Блокирующая функция для получения информации о видео с помощью yt-dlp.
    Выполняется в отдельном потоке через run_in_executor.
    """
    # thread_id = asyncio.get_running_loop()._thread_id
    thread_id = threading.get_ident()
    logger.info(f"[Поток ID: {os.getpid()}-{thread_id}] Начало fetch_video_info_blocking для URL: {video_url}")

    ydl_opts_info = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'discard_in_playlist',  # Получать информацию только о видео, не о плейлистах целиком
        'dumpjson': False,  # Мы хотим получить dict, а не JSON строку
        'skip_download': True,  # Не скачивать видео, только информацию
        'forcejson': False,
        'socket_timeout': 60,  # Увеличенный таймаут для сетевых операций (в секундах)
    }
    if os.path.exists(COOKIES_FILE_PATH):
        ydl_opts_info['cookiefile'] = COOKIES_FILE_PATH
        logger.info(f"[Поток ID: {os.getpid()}-{thread_id}] Используется файл cookies: {COOKIES_FILE_PATH} для info")
    else:
        logger.warning(
            f"[Поток ID: {os.getpid()}-{thread_id}] Файл cookies не найден, информация может быть неполной или вы столкнетесь с ограничениями.")

    try:
        logger.info(f"[Поток ID: {os.getpid()}-{thread_id}] YoutubeDL инициализирован. Вызов extract_info...")
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
        logger.info(
            f"[Поток ID: {os.getpid()}-{thread_id}] Информация успешно получена для {video_url}. Название: {info_dict.get('title')}")
        return info_dict
    except yt_dlp.utils.DownloadError as e:
        logger.error(
            f"[Поток ID: {os.getpid()}-{thread_id}] Ошибка DownloadError при получении информации для {video_url}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении информации от YouTube: {str(e)}")
    except Exception as e:
        logger.error(
            f"[Поток ID: {os.getpid()}-{thread_id}] Непредвиденная ошибка при получении информации для {video_url}: {e}")
        raise HTTPException(status_code=500, detail=f"Непредвиденная ошибка сервера при обработке URL: {str(e)}")


def get_download_link_blocking(video_url: str, format_itag: str) -> Dict[str, Any]:
    """
    Блокирующая функция для получения прямой ссылки на скачивание определенного формата.
    """
    # thread_id = asyncio.get_running_loop()._thread_id
    thread_id = threading.get_ident()
    logger.info(
        f"[Поток ID: {os.getpid()}-{thread_id}] Начало get_download_link_blocking для URL: {video_url}, ITAG: {format_itag}")
    ydl_opts_download = {
        'quiet': True,
        'no_warnings': True,
        'format': format_itag,
        # 'geturl': True, # Не работает как ожидается для получения прямой ссылки без скачивания
        # Вместо 'geturl', мы будем извлекать URL из информации о выбранном формате
        'skip_download': True,  # Убедимся, что не скачиваем
        'dumpjson': False,
        'forcejson': False,
        'socket_timeout': 60,  # Увеличенный таймаут
    }
    if os.path.exists(COOKIES_FILE_PATH):
        ydl_opts_download['cookiefile'] = COOKIES_FILE_PATH
        logger.info(
            f"[Поток ID: {os.getpid()}-{thread_id}] Используется файл cookies: {COOKIES_FILE_PATH} для download link")

    try:
        logger.info(
            f"[Поток ID: {os.getpid()}-{thread_id}] YoutubeDL для ссылки инициализирован. Вызов extract_info...")
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            info = ydl.extract_info(video_url, download=False)

        # Ищем запрошенный формат в списке форматов
        selected_format_info = None
        if 'formats' in info:
            for f in info['formats']:
                if f.get('format_id') == format_itag:
                    selected_format_info = f
                    break

        # Если формат не найден напрямую, yt-dlp мог выбрать "лучший" на основе itag,
        # и информация будет в корневом словаре info (если itag указывал на один поток)
        if not selected_format_info and info.get('format_id') == format_itag:
            selected_format_info = info

        if selected_format_info and 'url' in selected_format_info:
            download_url = selected_format_info['url']
            # yt-dlp может не предоставить 'title' и 'ext' для отдельных форматов напрямую,
            # берем их из общего info_dict
            filename = ydl.prepare_filename(info, outtmpl='%(title)s.%(ext)s')
            # Если ext не определился (например, для очень специфичных itag), ставим mp4 по умолчанию
            if '.' not in filename:
                filename = f"{info.get('title', 'video')}.{selected_format_info.get('ext', 'mp4')}"

            logger.info(
                f"[Поток ID: {os.getpid()}-{thread_id}] Ссылка на скачивание получена для {video_url} (itag: {format_itag}): {download_url[:100]}...")
            return {"url": download_url, "filename": filename}
        else:
            logger.error(
                f"[Поток ID: {os.getpid()}-{thread_id}] Не удалось найти URL для скачивания формата {format_itag} для видео {video_url}. Info: {selected_format_info}")
            raise HTTPException(status_code=404,
                                detail=f"Не удалось получить ссылку на скачивание для формата {format_itag}. Возможно, формат не доступен или требует дополнительной обработки.")

    except yt_dlp.utils.DownloadError as e:
        logger.error(
            f"[Поток ID: {os.getpid()}-{thread_id}] Ошибка DownloadError при получении ссылки для {video_url} (itag: {format_itag}): {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка yt-dlp при получении ссылки на скачивание: {str(e)}")
    except Exception as e:
        logger.error(
            f"[Поток ID: {os.getpid()}-{thread_id}] Непредвиденная ошибка при получении ссылки для {video_url} (itag: {format_itag}): {e}")
        raise HTTPException(status_code=500, detail=f"Непредвиденная ошибка сервера при получении ссылки: {str(e)}")


# --- Эндпоинты API ---

@app.get("/api/video-info", response_model=VideoDetails)
async def get_video_information(url: str = Query(..., description="URL YouTube видео")):
    """
    Получает подробную информацию о YouTube видео, включая доступные форматы.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Параметр 'url' не может быть пустым.")
    logger.info(f"Получен запрос /api/video-info для URL: {url}")

    try:
        # Выполняем блокирующую операцию в отдельном потоке
        info_dict = await asyncio.to_thread(fetch_video_info_blocking, url)

        formats_info: List[VideoFormatInfo] = []
        if info_dict and 'formats' in info_dict:
            for f_data in info_dict['formats']:
                # Пропускаем форматы только с аудио или только с видео, если они не комбинированные
                # или если у них нет четкого vcodec и acodec (часто это адаптивные DASH потоки)
                # if (f_data.get('vcodec') != 'none' and f_data.get('acodec') != 'none') or \
                #    (f_data.get('vcodec') != 'none' and not f_data.get('acodec')) or \
                #    (f_data.get('acodec') != 'none' and not f_data.get('vcodec')): # Это условие пропускало бы аудио/видео only. Пока оставим все.

                formats_info.append(VideoFormatInfo(
                    itag=f_data.get('format_id', 'N/A'),
                    resolution=f_data.get('resolution', f_data.get('width') and f_data.get(
                        'height') and f"{f_data['width']}x{f_data['height']}"),
                    vcodec=f_data.get('vcodec'),
                    acodec=f_data.get('acodec'),
                    ext=f_data.get('ext', 'N/A'),
                    filesize=f_data.get('filesize') or f_data.get('filesize_approx'),
                    format_note=f_data.get('format_note'),
                    fps=f_data.get('fps'),
                    abr=f_data.get('abr'),
                    tbr=f_data.get('tbr')
                ))

        if not formats_info:
            logger.warning(f"Не найдено подходящих форматов для {url} в info_dict: {info_dict}")
            # Проверяем, есть ли сообщение об ошибке в самом info_dict (например, от yt-dlp)
            if '_type' in info_dict and info_dict['_type'] == 'youtube' and not info_dict.get('entries'):
                # Это может быть приватное видео или другая проблема, которую yt-dlp вернул как ошибку на уровне видео
                pass  # Ошибка будет обработана выше в fetch_video_info_blocking
            raise HTTPException(status_code=404,
                                detail="Не удалось извлечь доступные форматы для этого видео. Возможно, видео недоступно или защищено.")

        return VideoDetails(
            title=info_dict.get('title', 'Без названия'),
            thumbnail_url=info_dict.get('thumbnail', ''),
            duration=int(info_dict.get('duration', 0)),
            uploader=info_dict.get('uploader'),
            description=info_dict.get('description'),
            available_formats=formats_info
        )
    except HTTPException as httpe:  # Перехватываем наши же HTTP исключения
        raise httpe
    except Exception as e:
        logger.error(f"Критическая ошибка в эндпоинте /api/video-info для URL {url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера при обработке вашего запроса: {str(e)}")


@app.get("/api/download-link", response_model=DownloadResponse)
async def get_download_link(url: str = Query(..., description="URL YouTube видео"),
                            itag: str = Query(..., description="itag формата для скачивания")):
    """
    Получает прямую ссылку на скачивание для указанного URL и itag.
    Эта ссылка обычно временная.
    """
    if not url or not itag:
        raise HTTPException(status_code=400, detail="Параметры 'url' и 'itag' обязательны.")
    logger.info(f"Получен запрос /api/download-link для URL: {url}, ITAG: {itag}")

    try:
        result = await asyncio.to_thread(get_download_link_blocking, url, itag)
        if result and "url" in result and "filename" in result:
            # Прямой редирект может быть не лучшим решением для API,
            # так как клиент может захотеть сначала получить ссылку.
            # return RedirectResponse(url=result["url"], status_code=307)
            # Вместо этого вернем JSON с ссылкой
            logger.info(
                f"Успешно сформирован ответ для /api/download-link: {result['url'][:100]}... Файл: {result['filename']}")
            return DownloadResponse(
                message="Ссылка на скачивание успешно получена.",
                direct_download_url=result["url"],
                filename=result["filename"]
            )
        else:
            logger.error(
                f"get_download_link_blocking не вернул ожидаемый результат для {url} itag {itag}. Результат: {result}")
            raise HTTPException(status_code=500,
                                detail="Не удалось получить корректную ссылку на скачивание от обработчика.")

    except HTTPException as httpe:
        logger.warning(f"HTTPException при получении ссылки для {url} itag {itag}: {httpe.detail}")
        raise httpe
    except Exception as e:
        logger.error(f"Критическая ошибка в эндпоинте /api/download-link для URL {url} itag {itag}: {e}", exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Внутренняя ошибка сервера при получении ссылки на скачивание: {str(e)}")


@app.get("/")
async def root():
    return {"message": "YouTube Downloader API запущен. Используйте /docs для просмотра доступных эндпоинтов."}


# --- Для запуска через `python main.py` ---
if __name__ == "__main__":
    import uvicorn

    logger.info("Убедитесь, что yt-dlp установлен: pip install yt-dlp")
    logger.info(
        "Для работы с некоторыми форматами может потребоваться FFmpeg, убедитесь, что он в PATH или указан в ydl_opts.")
    if not os.path.exists(COOKIES_FILE_PATH):
        logger.warning(
            f"--- ВНИМАНИЕ: Файл '{COOKIES_FILE_PATH}' не найден. Создайте его и поместите туда свои YouTube cookies в формате Netscape для обхода ограничений и доступа к приватным видео. ---")
    else:
        logger.info(f"--- Файл cookies '{COOKIES_FILE_PATH}' найден и будет использоваться. ---")

    uvicorn.run(app, host="0.0.0.0", port=8000)
