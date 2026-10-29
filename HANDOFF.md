# ทันท่วงที — project handoff (for AI agents)

Last updated: 26 Oct 2026 · code revision **r10** (see `VERSION`, `CHANGELOG.md`)
Owner: Seven (Thailand, Asia/Bangkok time). Personal business, not affiliated with any employer.

---

## 1. What this project is

An automated Thai **scam-awareness short-video channel** called **ทันท่วงที** ("in the nick of time").
On each posting day the system, with no human step:

1. **Researches** one scam case or warning reported in Thailand in the last 3 days (Claude API + web search).
2. **Writes** a 60–80 s documentary-style Thai script (scenes, chat reenactment, data graphics, a rule),
   then runs a **fact-check / natural-Thai editor pass** against the sources.
3. **Voices** it in Thai (ElevenLabs), with word timings for synced captions.
4. **Renders** a vertical 1080×1920 animated video in a **Constructivist propaganda poster** style
   (red/black/cream, halftone photomontage, slogans on slanted bars, red wedge transitions) with a
   synthesized sound-effects score. Falls back to a simpler "classic" yellow phone-chat look if the
   new renderer fails.
5. **Sends** the video + title/description/sources to the owner's **Telegram**.
6. **Auto-posts** at ~18:23 to **YouTube Shorts, Facebook Reels, Instagram Reels, TikTok** via
   Upload-Post (unless the owner replies `skip`, or a safety check holds it).
7. **Weekly report** (Mondays) to Telegram: followers, per-video views/likes/comments/shares,
   Claude's analysis; lessons are fed back into next week's scripts.

**Goal:** grow views, then earn (Facebook content monetization, sponsors, talks/workshops, a digital
product / LINE OA funnel — not started yet).

**Owner preferences (important):** direct, concise, bullet-style answers; simple defensible solutions;
**no service-plan upgrades** (lower frequency instead); fully automatic posting with **no daily "ok"**;
keep the Constructivist look for now; keep current logo/banners.

---

## 2. Services and accounts (no secret values in this file)

| Service | Used for | Identifier / notes |
|---|---|---|
| **GitHub** (Free plan) | Code + scheduled automation (GitHub Actions) | Private repo **`Toodmuk/scamshorts`**. Limits: 2,000 Actions min/month, 500 MB artifact storage |
| **Anthropic Claude API** | Research (web search), script writing, editor pass, weekly analysis | Model `claude-sonnet-5-5`, tool `web_search_20250305`. Prepaid credits at platform.claude.com. ~$0.3–0.6 per video |
| **ElevenLabs** (Starter, 30k credits/month) | Thai narration | Model `eleven_v3`, voice ID `deCz1h6mjB7HnY2xQz08`. Uses `/v1/text-to-speech/{voice}/with-timestamps`; credit pacing reads `/v1/user/subscription` (needs key permission **User: Read**, optional — otherwise uses its own count) |
| **Telegram bot** | Daily preview, posting results, warnings, weekly report; owner replies `ok` / `skip` | Bot "Media bot" **@worachit_media_bot**; messages go to the owner's private chat (`TELEGRAM_CHAT_ID`). Replies are read with `getUpdates` (no webhook) |
| **Upload-Post** (upload-post.com) | One API call posts to all platforms; analytics for the report | Profile **`tuntuangtee`**. API base `https://api.upload-post.com/api`: `POST /upload`, `GET /uploadposts/status`, `GET /uploadposts/post-analytics/{request_id}`, `GET /analytics/{profile}`. **Must be a paid plan** (Free = 10 uploads/month and no TikTok) |
| **YouTube** | Shorts | Channel ทันท่วงที (handle around @tantuangtee) |
| **Facebook** | Reels | Page **ทันท่วงที** (created from the owner's personal account). Reels max 90 s |
| **Instagram** | Reels | Professional (Creator) account, linked to the Facebook Page |
| **TikTok** | Videos | Account ทันท่วงที — **connection to Upload-Post not yet confirmed** |
| **Natural Earth** | Thailand map/province shapes | Public domain; bundled in `assets/` and `web/thmap.js` |
| **Fonts** | Kanit (Thai), Anton (numbers), IBM Plex Sans Thai, Chakra Petch | OFL; bundled in `web/fonts/` and `assets/fonts/` |

---

## 3. GitHub secrets (Settings → Secrets and variables → Actions)

| Secret | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | |
| `ELEVENLABS_API_KEY` | yes | Text to Speech permission; add **User: Read** for exact credit pacing |
| `TELEGRAM_BOT_TOKEN` | yes | From @BotFather |
| `TELEGRAM_CHAT_ID` | yes | Owner's chat id |
| `UPLOAD_POST_API_KEY` | yes | |
| `UPLOAD_POST_USER` | yes | `tuntuangtee` |
| `FACEBOOK_PAGE_ID` | optional | Only for Facebook follower counts in the weekly report |

The voice ID is **not** a secret (it's in `settings.py`). An old `ELEVENLABS_VOICE_ID` secret may exist and is unused.

---

## 4. Schedule (Asia/Bangkok)

| When | Workflow | What |
|---|---|---|
| 06:17 daily (cron `17 23 * * *` UTC) | `daily.yml` "Daily Short" | Only on `POST_DAYS` (Mon, Wed, Fri, Sun): research → voice → render → Telegram. Other days exit in seconds |
| 12:23, 18:23, 19:23, 20:23, 21:23 (cron `23 5,11,12,13,14 * * *`) | `post.yaml` "Post Short" | On posting days: posts at the first check from 18:00 if not held/skipped; never twice |
| Mondays 09:17 (cron `17 2 * * 1`) | `report.yml` "Weekly report" | Stats + analysis to Telegram; saves `data/stats.json`, `data/insights.txt` |
| Manual only | `check.yml` "Check setup" | Tests every key with tiny requests, renders a silent sample, reports which video style ran |

Cron minutes avoid :00 because GitHub delays/drops top-of-hour runs. Manual "Run workflow" works on any day.

---

## 5. Repository layout

```
run.py              Morning job: credit budget -> research/script -> voice -> render -> Telegram
post.py             Posting job: safety checks, ok/skip from Telegram, auto-post at AUTO_POST_HOUR
report.py           Weekly report (Upload-Post analytics + Claude analysis) -> Telegram
check.py            Setup check (keys, model, web search, voice, fonts, renderer, Telegram)
schedule.py         POST_DAYS logic; `python schedule.py` exits 0 on a posting day (used by workflows)
settings.py         THE ONLY CONFIG FILE (no secrets)
requirements.txt    Pinned: anthropic 1.9.0, requests 2.33.1, pillow 12.1.1, pythainlp 5.3.8, json-repair 0.64.2
shorts/
  script.py         Claude prompt (SYSTEM, EDITOR), schema, validation; script returned via the
                    `submit_script` tool (valid JSON) with json-repair + retry fallback
  voice.py          ElevenLabs TTS (+timestamps), credit budget(), usage log, 88 s speed cap
  render.py         Entry: tries the Node renderer, falls back to the classic Pillow renderer;
                    marks the renderer used in script.json; classic renderer + SFX + mixing helpers
  render_web.py     Bridge to Node: builds job.json (timings, word times, Thai word breaks), runs
                    web/render.js, mixes voice + effects (+music), loudnorm -14 LUFS, muxes short.mp4
  beats.py          Classic-renderer infographics + validate() for visual beats
  text.py           Thai wrapping (pythainlp + custom dictionary), emoji cleanup
  publish.py        Upload-Post posting (captions per platform, AI labels, results, request_id, usage)
  deliver.py        Telegram: send video, notify(), read ok/skip replies
web/                Constructivist renderer (Node, no browser)
  explainer.js      Engine: beats (hook, chat, proof, flow/loop, money, stat, compare, bars, percent,
                    map, reveal, rule, CTA), camera drift, wedge transitions, captions, sound score
  harness.js        "H" helper library from the AI Style Atlas kit (unchanged)
  sound.js          SOUND kit (Web Audio, synthesized; unchanged)
  render.js         Renders frames (node-canvas, 15 fps on twos -> 30 fps H.264, 4 Mbps cap) + SFX WAV
                    (node-web-audio-api OfflineAudioContext); runs without SFX if audio can't load
  thmap.js          Thailand provinces for the map beat
  fonts/            Kanit 500/700/800/900, Anton
  package.json, package-lock.json   canvas 3.2.3, node-web-audio-api 2.2.0
assets/             Classic-renderer fonts, thailand_provinces.json, music/ (optional royalty-free mp3s)
samples/            sample_script.json (free silent test)
design/map-explainer/  Prototype of the next style (see section 10)
.github/workflows/  daily.yml, post.yaml (named post.yml in some bundles), report.yml, check.yml
data/               Live state written by the workflows (never overwrite from bundles):
  history.json      topics already covered
  posted.json       per date: status posted/skipped/no reply, title, hook, topic, request_id, results;
                    "held:<date>" keys for safety holds
  stats.json        weekly snapshots;  insights.txt  lessons for the script writer
  voice_usage.json  monthly voice characters (backup for credit pacing)
```

---

## 6. Settings (`settings.py`, current values)

| Key | Value | Meaning |
|---|---|---|
| `ELEVENLABS_VOICE_ID` / `ELEVENLABS_MODEL` | `deCz1h6mjB7HnY2xQz08` / `eleven_v3` | Voice |
| `CLAUDE_MODEL` / `WEB_SEARCH_TOOL` | `claude-sonnet-5-5` / `web_search_20250305` | Script writer |
| `NARRATOR` | `neutral` | No ครับ/ค่ะ (voice gender unknown); `male`/`female` possible |
| `NEWS_DAYS` | 3 | Look for news from the last N days first |
| `EDITOR_PASS` | True | Second Claude pass: fact-check + natural Thai |
| `RENDERER` | `constructivist` | or `classic` |
| `CHANNEL_NAME` | ทันท่วงที | End-card "กดติดตาม" line |
| `POST_DAYS` | `mon,wed,fri,sun` | ~17–18 videos/month (sized for current plans) |
| `VOICE_MONTHLY_CREDITS` / `VOICE_RESERVE` | 30000 / 2000 | Credit pacing fallback + spare |
| `MAX_SECONDS` | 88 | Facebook Reels limit 90 s; narration sped up ≤1.25× if longer |
| `POST_MODE` | `auto` | `approve` = only after "ok" |
| `AUTO_POST_HOUR` / `POST_TIME` | 18 / "18:30" | Auto-post hour; time shown in Telegram |
| `PLATFORMS` | `youtube,facebook,instagram,tiktok` | Unconnected platforms are reported as SKIPPED |
| `LABEL_AI` | True | AI-content labels on YouTube/TikTok |

---

## 7. Safety, limits and fallbacks

- **Safety hold (auto mode):** not auto-posted if no source URLs, the editor pass didn't run, or the
  classic fallback renderer was used → Telegram asks for `ok` once. `skip` cancels any day.
- **Content rules (in the prompt):** facts only from sources; links masked (`https://xxxxx.xx/...`),
  phones masked; fictional sender names; generic impersonated orgs in chat mock-ups; no emoji;
  every post ends with the 1441 hotline (AOC anti-online-scam centre).
- **Fallbacks:** renderer → classic look (+Telegram ⚠️ with the error line); SFX engine can't load →
  new look without SFX; script JSON → tool call / repair / 3 retries; editor fails → draft kept
  (and held); Telegram errors never fail the video; TikTok daily cap → video lands in TikTok drafts
  (flagged in Telegram).
- **Monthly budget at 4 videos/week:** ElevenLabs ~18k of 30k; GitHub ~450 of 2,000 min; storage
  ~120 MB of 500 MB (videos kept 3 days); Claude ~$5–11; Upload-Post usage shown after each post.

---

## 8. Current status and BLOCKING POINT

**Blocking:** the new Constructivist renderer has **never succeeded on GitHub's machines yet**.

- Last real run (r9): research, script, voice, Telegram all worked, but Telegram said
  **"วันนี้ใช้ระบบตัดต่อสำรอง"** and the video was in the old classic look.
- Most likely cause (found by inspecting the binaries): `node-web-audio-api`'s Linux binary needs
  **`libasound.so.2`** (ALSA), which GitHub's Ubuntu 24.04 runners don't install by default.
- **r10 (built, tested locally, NOT yet uploaded/verified):** workflows install `libasound2t64`;
  if audio still can't load the video keeps the new look without SFX; the Telegram warning now
  shows the exact error line.
- That run's video is **held** by the safety check (classic renderer) — owner should reply `ok` or `skip`.

**Next actions, in order:**
1. Owner uploads r10 to the repo (Add file → Upload files → drag everything → Commit).
2. Actions → **Check setup** → expect ✅ "Video style: constructivist".
3. Actions → **Daily Short** (manual) → in the log expect `Constructivist render OK` and
   `Renderer: constructivist`; video in Telegram in the new look.
4. If it still falls back: read the line after "สาเหตุ:" in Telegram / the log and fix
   (other candidates: render time vs the 30-min subprocess timeout in `render_web.py`, missing
   fonts, npm install problems).
5. Verify posting end to end: reply `ok`, Actions → **Post Short** → Telegram shows links for
   youtube/facebook/instagram/tiktok.
6. Actions → **Weekly report** once to verify analytics parsing on real data.

**Unverified on real infrastructure (tested only with simulations):** render time on GitHub's runner
(expected ~10–20 min for 60–80 s), ElevenLabs subscription endpoint permission, Upload-Post analytics
response shapes, TikTok posting.

**Owner-side items to confirm:** Upload-Post plan is paid; TikTok account created, public, and
connected to profile `tuntuangtee`; ElevenLabs key has User: Read (optional); Claude credit topped up
(auto-reload recommended).

---

## 9. How to test (agent with a shell)

```bash
sudo apt-get install -y ffmpeg libraqm0 libfribidi0 libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev libasound2t64
pip install -r requirements.txt
npm ci --prefix web
python run.py --script samples/sample_script.json --no-voice     # free silent preview -> out/<date>/short.mp4
python check.py                                                  # needs the secrets as env vars
POST_NOW=2026-10-26T18:23:00 POST_ANY_DAY=1 python post.py out --dry-run
node web/render.js out/<date>/tmp/job.json                       # renderer only (job.json written by render_web.py)
TT_NO_AUDIO=1 node web/render.js job.json                        # simulate the SFX engine missing
```
Rendering ~60 s of video takes ~6 min on a fast machine (single-threaded JS); keep commands under any
tool timeouts (run detached and poll).

---

## 10. Backlog

1. **Unblock the renderer on GitHub** (section 8).
2. **Map-explainer style + mascot น้องทัน** — the owner sent references (map-based explainers with a
   presenter character) saying "people like more". Storyboard published, **awaiting approval**:
   https://claude.ai/artifact/Qt2Non17PvSPsxJ63L91aP. Prototype code: `design/map-explainer/`.
   Plan: port into `web/explainer.js` as a theme (`RENDERER = "map"`), reuse beats/timing/sound,
   mouth movement from narration loudness, Natural Earth only (no street level / 3D; paid tiles not
   allowed by the "no plan upgrades" rule). The owner later said to keep Constructivist for now —
   confirm before switching.
3. **Money:** request Facebook content monetization when eligible; LINE OA + free anti-scam checklist;
   workshops/talks; non-security sponsors.
4. Optional: `FACEBOOK_PAGE_ID` secret; refresh logo/banners to the new style (owner: keep for now).

---

## 11. Brand and assets

- Channel: **ทันท่วงที**; Upload-Post profile `tuntuangtee`; handles around `@tantuangtee`.
- Logo: black rounded "ทัน" tile on yellow (#FFC700) with a red (#D6241C) "!" alert badge. Profile
  picture, YouTube banner, Facebook cover and bios were made in chat (files with the owner).
- Video style (Constructivist): red `#c8281e`, black `#1d1a17`, cream `#e9dcbc`; Kanit 900 slogans,
  Anton numbers; storyboard: https://claude.ai/artifact/6TF2pMcT3vcoTFdrSdiTSp
- Cost tracking: `channel_cost_tracker.xlsx` (with the owner; 5 channel sheets + summary).

---

## 12. Revision history (short)

- **r10** libasound fix for the Node renderer; render without SFX if needed; clear fallback reason.
- **r9** script returned via `submit_script` tool (fixes "no JSON object" / "Expecting ',' delimiter").
- **r8** TikTok; SKIPPED for unconnected platforms; TikTok inbox fallback; Upload-Post usage in Telegram.
- **r7** POST_DAYS (4/week), voice-credit pacing, 88 s cap, 5 posting checks/day, 3-day artifacts.
- **r6** auto-posting with safety hold; weekly report with feedback loop; 60–80 s scripts; new charts.
- **r5** Constructivist renderer (Node) with classic fallback.
- Earlier: classic renderer, Telegram approval, hourly posting fix, setup check, animated chat style.
