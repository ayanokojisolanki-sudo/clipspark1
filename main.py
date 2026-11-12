from pathlib import Path
import re, shutil, subprocess, uuid, json
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from youtube_transcript_api import YouTubeTranscriptApi

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "app" / "static"
UPLOADS = BASE / "data" / "uploads"
OUTPUTS = BASE / "data" / "clips"
UPLOADS.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ClipSpark — AI Shorts Clipper")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/clips", StaticFiles(directory=OUTPUTS), name="clips")

def video_id_from_url(url):
    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m: return m.group(1)
    raise HTTPException(400, "Enter a valid YouTube video URL.")

def transcript_for(video_id):
    try:
        rows = YouTubeTranscriptApi().fetch(video_id)
        return [{"start": float(s.start), "duration": float(s.duration), "text": str(s.text)} for s in rows]
    except Exception as e:
        raise HTTPException(422, "Captions are unavailable or access was blocked for this video. Try a video with public captions. " + str(e)[:180])

def score(text):
    t = text.lower()
    triggers = ["why", "how", "secret", "mistake", "never", "best", "worst", "truth", "surprising", "important", "here's"]
    return min(len(text)/110, 2) + sum(.4 for w in triggers if w in t) + min(text.count("!")*.2 + text.count("?")*.2, .8)

def find_clips(rows, count=8):
    if not rows: return []
    duration = max(x["start"] + x["duration"] for x in rows)
    candidates, start = [], 0.0
    while start + 20 <= duration:
        end = min(start + 45, duration)
        text = " ".join(x["text"] for x in rows if x["start"] < end and x["start"] + x["duration"] > start).strip()
        if len(text.split()) >= 18:
            candidates.append({"start": round(start,1), "end": round(end,1), "duration": round(end-start,1), "score": round(score(text),2), "text": text[:650]})
        start += 8
    chosen = []
    for c in sorted(candidates, key=lambda x:x["score"], reverse=True):
        if all(c["end"] <= x["start"] or c["start"] >= x["end"] for x in chosen):
            chosen.append(c)
        if len(chosen) >= max(1, min(int(count), 15)): break
    return sorted(chosen, key=lambda x:x["start"])

@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")

@app.get("/manifest.webmanifest")
def manifest():
    from fastapi.responses import JSONResponse
    return JSONResponse({
        "name":"ClipSpark AI Shorts Clipper","short_name":"ClipSpark",
        "start_url":"/","display":"standalone","background_color":"#090d18",
        "theme_color":"#090d18","icons":[]
    })

@app.get("/api/health")
def health():
    return {"ok":True, "ffmpeg":bool(shutil.which("ffmpeg"))}

@app.post("/api/highlights")
def highlights(url: str = Form(...), count: int = Form(8)):
    vid = video_id_from_url(url)
    rows = transcript_for(vid)
    return {"video_id":vid, "clips":find_clips(rows,count), "caption_segments":len(rows)}

@app.post("/api/render")
async def render(video: UploadFile = File(...), clips_json: str = Form(...)):
    if not shutil.which("ffmpeg"):
        raise HTTPException(500, "FFmpeg is missing on the server.")
    try: clips = json.loads(clips_json)
    except Exception: raise HTTPException(400, "Invalid selected clips.")
    if not isinstance(clips,list) or not clips: raise HTTPException(400,"Select at least one clip.")
    ext = Path(video.filename or "source.mp4").suffix.lower()
    if ext not in {".mp4",".mov",".mkv",".webm"}: raise HTTPException(400,"Upload MP4, MOV, MKV, or WEBM.")
    job = uuid.uuid4().hex
    source = UPLOADS / f"{job}{ext}"
    with source.open("wb") as f: shutil.copyfileobj(video.file,f)
    out=[]
    for i,c in enumerate(clips[:15],1):
        start=max(0,float(c["start"])); dur=min(60,max(1,float(c["end"])-start))
        target=OUTPUTS/f"{job}_{i}.mp4"
        cmd=["ffmpeg","-y","-ss",str(start),"-i",str(source),"-t",str(dur),
             "-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
             "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac",
             "-movflags","+faststart",str(target)]
        p=subprocess.run(cmd,capture_output=True,text=True)
        if p.returncode: raise HTTPException(500,"FFmpeg error: "+p.stderr[-500:])
        out.append({"name":target.name,"url":f"/clips/{target.name}"})
    return {"clips":out}
