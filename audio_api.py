from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, StreamingResponse
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

AUDIO_FILE_PATH = "C:/Users/Partha/Music/recordings/kho gye.mp3"  # Make sure this is the CORRECT path

@app.get("/audio")
async def get_audio():
    """
    Endpoint to return an MP3 audio file (non-streaming).
    """
    if not os.path.exists(AUDIO_FILE_PATH):
        return Response(status_code=404, content="Audio file not found")

    return FileResponse(AUDIO_FILE_PATH, media_type="audio/mpeg")

@app.get("/stream_audio")
async def stream_audio():
    """
    Endpoint to stream an MP3 audio file.
    """
    if not os.path.exists(AUDIO_FILE_PATH):
        return Response(status_code=404, content="Audio file not found")

    def audio_generator():
        with open(AUDIO_FILE_PATH, "rb") as f:
            while chunk := f.read(1024 * 64): # Read in 64KB chunks
                yield chunk

    return StreamingResponse(audio_generator(), media_type="audio/mpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) # Make sure the port is set as desired (e.g., 8001)
