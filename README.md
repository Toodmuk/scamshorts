# Scam Shorts — Plan A (lean test)

Every morning at 06:00 Bangkok time, GitHub runs this repo and makes one Thai
scam-awareness Short:

1. **Research** — Claude searches for a scam reported in Thailand in the last 14 days
   and writes the script (skips topics already covered).
2. **Voice** — ElevenLabs reads each line in Thai.
3. **Video** — reenacted SMS/LINE chat, red "มิจฉาชีพ" stamp at the reveal,
   end card with the rule + 1441. 1080×1920, ~30–45 s.
4. **Delivery** — video + title/description/sources sent to your Telegram,
   and saved in the GitHub Actions run.

You review, fact-check, and upload. Nothing posts automatically.

---

## Setup (about 45 minutes)

### 1. Get the keys
| Service | What to do | Cost |
|---|---|---|
| Anthropic | console.anthropic.com → create API key → add $5–10 credit | ~$3–10/mo |
| ElevenLabs | Starter plan → API key. Voice Library → filter Thai → add a voice → copy its Voice ID | $6/mo |
| Telegram (optional, recommended) | Chat with @BotFather → `/newbot` → copy token. Send your bot any message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id` | Free |

Test the Thai voice in ElevenLabs first. If it sounds off, try another voice — this
matters more than anything else in the pipeline.

### 2. Put the code on GitHub
Create a **private** repo and upload everything in this folder (including `.github/`).

### 3. Add secrets (API keys never go in the code)
Repo → Settings → Secrets and variables → Actions → New repository secret:

- `ANTHROPIC_API_KEY`
- `ELEVENLABS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Everything else (voice ID, models, posting mode) lives in **`settings.py`** —
the only file you need to edit.

### 4. Check setup (costs about $0.01)
Actions tab → **Check setup** → **Run workflow**. In ~3 minutes Telegram gets:
a ✅/❌ checklist (each ❌ says exactly what to fix), a voice sample, and a silent
sample video. Fix any ❌ and run it again until everything is ✅.

### 5. First real video
Actions tab → **Daily Short** → **Run workflow**. Takes ~3–5 minutes.
The video arrives in Telegram (also saved under the run's **Artifacts**).
From tomorrow it runs by itself at 06:00.

---

## Auto-posting to YouTube, Facebook, Instagram

Posting goes through **Upload-Post** (upload-post.com): one API call posts to every
platform through apps they've already had approved. (Posting through your own Google
project would lock YouTube uploads to private until Google audits it.)

**Daily flow**
- 06:00 — video arrives in Telegram with its sources.
- Reply **ok** to approve (or **skip**).
- 18:00 — the **Post Short** workflow posts it everywhere and sends you the links.

**Setup (~20 min)**
1. You need: a YouTube channel, a Facebook **Page** (Meta doesn't allow API posting
   to personal profiles), and an Instagram **Professional** account (Business or
   Creator) linked to that Page.
2. Sign up at upload-post.com → create a profile (e.g. `scamshorts`) → connect
   YouTube, Facebook and Instagram to it.
3. Dashboard → API Keys → create a key.
4. Add GitHub secrets: `UPLOAD_POST_API_KEY`, `UPLOAD_POST_USER` (the profile name).
   Add `FACEBOOK_PAGE_ID` only if you manage more than one Page.
5. Test: Actions → **Post Short** → Run workflow (after replying ok to today's video).

**Options** (edit `settings.py`)
| Setting | Default | Change to |
|---|---|---|
| `POST_MODE` | `approve` (posts only after you reply ok) | `auto` (posts unless you reply skip) |
| `PLATFORMS` | `youtube,facebook,instagram` | add `,tiktok` (paid Upload-Post plan) |
| `LABEL_AI` | `true` (marks AI voice on YouTube/TikTok) | `false` |

To change the posting time, edit the cron line in `.github/workflows/post.yml`
(`0 11 * * *` = 18:00 Bangkok).

## Daily routine (~5 min)
1. Watch the video in Telegram and open the sources.
2. **If the script says something the sources don't, reply skip.** Otherwise reply ok.

## Background music (optional)
Drop royalty-free `.mp3` files (e.g. from the YouTube Audio Library) into
`assets/music/`. One is picked at random and mixed in quietly.

## Test on your own computer
```bash
pip install -r requirements.txt          # also needs ffmpeg installed
python run.py --script samples/sample_script.json --no-voice   # free visual preview
python run.py                            # full run (needs the env vars above)
```

## Costs (1 Short/day)
- GitHub Actions: free (private repos get 2,000 min/month; this uses ~150)
- Claude API incl. web search: roughly $3–10/month
- ElevenLabs Starter: $6/month
- Upload-Post: free plan is too small for daily posting; paid from ~$16–24/month
- **Total: about $30–45/month**

## If something breaks
- **MISSING SECRET(S)** → the message names the missing key; add it in GitHub Secrets.
- **Model not found (Claude)** → change `CLAUDE_MODEL` in `settings.py` to a
  current model name from docs.claude.com.
- **Web search error** → check that web search is allowed for your org in the
  Anthropic Console, or update `WEB_SEARCH_TOOL` in `settings.py`.
- **Voice is wrong language / robotic** → change `ELEVENLABS_VOICE_ID` or
  `ELEVENLABS_MODEL` in `settings.py`.
- **Thai vowels/tone marks look misplaced** → the runner is missing `libraqm0`;
  the workflow installs it, so this only happens on local machines.

## Files
```
settings.py            THE ONLY FILE TO EDIT (voice, models, posting options)
check.py               setup check: tests every key for ~$0.01
run.py                 morning run: research -> video -> Telegram
post.py                evening run: check your ok/skip -> post everywhere
shorts/script.py       Claude research + script prompt (edit tone/rules here)
shorts/voice.py        ElevenLabs text-to-speech
shorts/render.py       frames + video (colours, layout)
shorts/deliver.py      Telegram preview + reading your ok/skip
shorts/publish.py      posting via Upload-Post
data/history.json      topics already covered (updated automatically)
data/posted.json       what was posted, with links (updated automatically)
samples/               example script for testing
```
