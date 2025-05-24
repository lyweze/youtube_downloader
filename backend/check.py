from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from rutube import Rutube
import os
import uvicorn
import logging
import re
from pathlib import Path
import time
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/api/video_info")
def get_video_info(video_url : str):
    rt_client = Rutube(video_url)
    with open('video.mp4', 'wb') as f:
        rt_client.get_best().download(stream=f)

    return FileResponse(path='video.mp4', filename='video.mp4', media_type='video/mp4')
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)