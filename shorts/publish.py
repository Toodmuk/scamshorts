"""Posts the Short to YouTube, Facebook and Instagram (optionally TikTok)
through Upload-Post, one API call for every platform."""
import os
import time

import requests

import settings

API = "https://api.upload-post.com/api"
KEY = os.getenv("UPLOAD_POST_API_KEY")      # secret - set in GitHub, not here
PROFILE = os.getenv("UPLOAD_POST_USER")
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")  # only needed if you manage several Pages
PLATFORMS = [p.strip() for p in settings.PLATFORMS.split(",") if p.strip()]
LABEL_AI = bool(settings.LABEL_AI)


def enabled():
    return bool(KEY and PROFILE)


def _captions(d):
    tags = " ".join(t for t in d["hashtags"] if t.lower() != "#shorts")
    body = f"{d['description']}\n\n{tags}".strip()
    plain = d["title"].replace("#shorts", "").strip()  # #shorts only means something on YouTube
    return {
        "title": d["title"][:100],                       # YouTube title
        "description": body,                             # YouTube + Facebook description
        "facebook_title": plain[:255],
        "instagram_title": f"{plain}\n\n{body}"[:2200],  # Instagram caption
        "tiktok_title": f"{plain} {tags}"[:2200],
    }


def build_form(d):
    """Form fields as a list of (name, value) pairs - platform[] and tags[] repeat."""
    form = [("user", PROFILE)]
    form += [("platform[]", p) for p in PLATFORMS]
    form += list(_captions(d).items())
    form += [("tags[]", t.lstrip("#")) for t in d["hashtags"] if t.lstrip("#") != "shorts"]
    form += [
        ("categoryId", "27"),            # Education
        ("privacyStatus", "public"),
        ("selfDeclaredMadeForKids", "false"),
        ("defaultLanguage", "th"),
        ("defaultAudioLanguage", "th"),
        ("containsSyntheticMedia", str(LABEL_AI).lower()),  # AI voice -> label it
        ("is_aigc", str(LABEL_AI).lower()),
        ("facebook_media_type", "REELS"),
        ("media_type", "REELS"),
        ("share_to_feed", "true"),
    ]
    if PAGE_ID:
        form.append(("facebook_page_id", PAGE_ID))
    return form


def _status(request_id, tries=20, wait=15):
    """Background uploads: poll until results come back (max ~5 min)."""
    for _ in range(tries):
        time.sleep(wait)
        r = requests.get(f"{API}/uploadposts/status", params={"request_id": request_id},
                         headers={"Authorization": f"Apikey {KEY}"}, timeout=60)
        if r.ok:
            j = r.json()
            if j.get("results") or str(j.get("status", "")).lower() in ("completed", "finished", "failed"):
                return j
    return {"note": f"still processing - check the Upload-Post dashboard (request {request_id})"}


def post(video_path, d):
    """Returns {platform: 'url' or 'ERROR: ...'}."""
    with open(video_path, "rb") as f:
        r = requests.post(f"{API}/upload", headers={"Authorization": f"Apikey {KEY}"},
                          data=build_form(d), files={"video": ("short.mp4", f, "video/mp4")},
                          timeout=600)
    try:
        j = r.json()
    except ValueError:
        raise RuntimeError(f"Upload-Post HTTP {r.status_code}: {r.text[:300]}")
    if not j.get("success"):
        raise RuntimeError(j.get("message") or j.get("error") or str(j)[:300])
    if j.get("request_id") and not j.get("results"):
        j = _status(j["request_id"])

    out = {}
    for platform, res in (j.get("results") or {}).items():
        if isinstance(res, dict) and res.get("success"):
            out[platform] = res.get("url") or "posted"
        else:
            err = res.get("error") if isinstance(res, dict) else res
            out[platform] = f"ERROR: {err}"
    if not out:
        out["upload-post"] = j.get("note") or str(j)[:300]
    return out
