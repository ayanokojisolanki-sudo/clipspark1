# AI Shorts Clipper — mobile web app

A phone-friendly web interface and FastAPI backend starter.

## What works in this starter
- Responsive Android-friendly dashboard.
- Accepts a YouTube URL and requests available captions from the backend.
- Suggests timestamped highlight windows from captions.
- Lets you upload a video file you own or are authorized to edit.
- Uses FFmpeg to render selected clips as vertical MP4 files.
- Provides download links for rendered clips.

## Important: URL-only limitation
A YouTube URL by itself does not grant permission to download the video or provide unrestricted access to its video stream. This app does not scrape or bypass YouTube's delivery controls. Caption access can also be unavailable or blocked. To render MP4 files, provide an authorized source video file (for example, your own original export). For a true URL-only workflow, connect an authorized video-source provider/API that grants access to the source media.

## Run on your computer
Requires Python 3.10+ and FFmpeg installed and on PATH.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Android/Termux or macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000` on the same device. To open it on your phone from another computer on the same Wi-Fi, use that computer's LAN IP and port 8000.

## Deploy online
Deploy the Python app to a host that supports persistent background/CPU workloads and FFmpeg (for example, a paid Render/Railway/Fly.io service). Set the start command to:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Free serverless/static hosting cannot run this video-processing backend reliably. Add persistent storage or object storage before production use.

## Notes
- This starter uses `youtube-transcript-api` for captions; availability is not guaranteed.
- Highlight selection is a heuristic. It is not a trained virality predictor.
- Rendering uses a center crop; face tracking and animated captions are not included yet.
- Keep uploads private, validate file sizes, add authentication/rate limits, and automatically delete temporary files before public launch.
