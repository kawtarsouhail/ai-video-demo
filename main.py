import os, subprocess, uuid, requests, edge_tts, shutil
from fastapi import FastAPI
from fastapi.responses import FileResponse


import asyncio
from gtts import gTTS

async def tts(text, mp3):
    try:
        await edge_tts.Communicate(text, VOICE, rate="-8%", pitch="-2Hz").save(mp3)
    except Exception as e:
        print(f"edge-tts failed ({type(e).__name__}); falling back to gTTS")
        await asyncio.to_thread(lambda: gTTS(text, lang="ar").save(mp3))
app = FastAPI()
BASE = os.path.dirname(os.path.abspath(__file__))
PIXABAY = os.environ["PIXABAY_KEY"]
VOICE = "ar-SA-ZariyahNeural"

@app.post("/render")
async def render(body: dict):
    job = f"/tmp/{uuid.uuid4().hex}"
    os.makedirs(job)
    clips = []
    for s in body["scenes"]:
        n = s["number"]
        mp3, img, clip = f"{job}/{n}.mp3", f"{job}/{n}.jpg", f"{job}/{n}.mp4"
        await tts(s["text_ar"], mp3)
        r = requests.get("https://pixabay.com/api/", params={"key": PIXABAY, "q": s["keyword_en"], "image_type": "photo", "orientation": "horizontal", "per_page": 3}).json()
        open(img, "wb").write(requests.get(r["hits"][0]["largeImageURL"]).content)
        subprocess.run(["/usr/bin/ffmpeg", "-y", "-loop", "1", "-i", img, "-i", mp3,
            "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-pix_fmt", "yuv420p",
            "-shortest", clip], check=True)
        clips.append(clip)
    with open(f"{job}/list.txt", "w") as f:
        f.writelines(f"file '{c}'\n" for c in clips)
    out = f"{job}/final.mp4"
    subprocess.run(["/usr/bin/ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{job}/list.txt", "-c", "copy", out], check=True)
    

    os.makedirs(f"{BASE}/output", exist_ok=True)
    with open(f"{job}/mp3list.txt", "w") as f:
        f.writelines(f"file '{job}/{s['number']}.mp3'\n" for s in body["scenes"])
    subprocess.run(["/usr/bin/ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{job}/mp3list.txt", "-c", "copy", f"{BASE}/output/narration.mp3"], check=True)
    shutil.copy(out, f"{BASE}/output/final.mp4")
    return FileResponse(out, media_type="video/mp4")
