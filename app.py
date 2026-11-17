"""Minimal yt-dlp connectivity test for Abasthan.

Purpose: ONLY verify whether yt-dlp running on Abasthan's servers can
extract a YouTube stream URL (i.e. the datacenter IP is not blocked).
This is NOT a YouTube frontend and does NOT proxy/stream any video:
the /yt-test endpoint returns JSON diagnostics only. No media is relayed
(the only outbound media check is a 1-byte Range probe of the extracted
URL, to prove reachability).
"""
import os
import time

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

TEST_VIDEO = "https://www.youtube.com/watch?v=hQ4-H-nNNz4"
# Format string used by the real Tube app (yt_video in app.py)
REAL_FORMAT = "bv[height<=720]+ba/b[acodec!=none]/b"


@app.route("/")
def index():
    try:
        import yt_dlp
        ver = yt_dlp.version.__version__
    except Exception as e:  # pragma: no cover
        ver = "import-failed: %s" % e
    return jsonify({
        "ok": True,
        "service": "abasthan-yt-test",
        "yt_dlp_version": ver,
        "test_endpoint": "/yt-test",
        "note": "metadata extraction test only, no streaming/proxy",
    })


def _probe(stream_url):
    """1-byte range probe: proves reachability, downloads no media."""
    try:
        r = requests.get(
            stream_url,
            headers={"Range": "bytes=0-0", "User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        out = {
            "status": r.status_code,
            "content_type": r.headers.get("Content-Type"),
            "reachable": r.status_code in (200, 206),
        }
        r.close()
        return out
    except Exception as e:
        return {"error": str(e)[:300], "reachable": False}


@app.route("/yt-test")
def yt_test():
    url = request.args.get("url") or TEST_VIDEO
    started = time.time()
    result = {"test_url": url, "real_app_format": REAL_FORMAT}
    from yt_dlp import YoutubeDL

    base = {"quiet": True, "no_warnings": True, "noplaylist": True,
            "socket_timeout": 20, "retries": 1}

    # Step A: unrestricted extraction - what does YouTube offer this IP at all?
    try:
        with YoutubeDL(dict(base)) as ydl:
            info = ydl.extract_info(url, download=False)
        result["extract_ok"] = True
        result["title"] = info.get("title")
        result["duration_sec"] = info.get("duration")
        fmts = info.get("formats") or []
        result["formats_total"] = len(fmts)
        result["formats_with_video"] = sum(
            1 for f in fmts if f.get("vcodec") not in (None, "none"))
        result["formats_with_audio"] = sum(
            1 for f in fmts if f.get("acodec") not in (None, "none"))
        result["format_ids_sample"] = [
            f.get("format_id") for f in fmts[:15]]
    except Exception as e:
        result["extract_ok"] = False
        result["error"] = str(e)[:800]
        result["elapsed_sec"] = round(time.time() - started, 2)
        return jsonify(result)

    # Step B: the real app's format selection - would playback work?
    try:
        with YoutubeDL(dict(base, format=REAL_FORMAT)) as ydl:
            vinfo = ydl.extract_info(url, download=False)
        result["real_format_ok"] = True
        stream_url = ""
        if vinfo.get("requested_formats"):
            result["requested_format_ids"] = [
                f.get("format_id") for f in vinfo["requested_formats"]]
            stream_url = vinfo["requested_formats"][0].get("url") or ""
        else:
            result["format_id"] = vinfo.get("format_id")
            result["ext"] = vinfo.get("ext")
            stream_url = vinfo.get("url") or ""
        result["stream_host"] = (
            stream_url.split("/")[2] if "://" in stream_url else "")
        if stream_url:
            result["stream_probe"] = _probe(stream_url)
    except Exception as e:
        result["real_format_ok"] = False
        result["real_format_error"] = str(e)[:800]

    result["elapsed_sec"] = round(time.time() - started, 2)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), threaded=True)
