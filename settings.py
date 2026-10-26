# ============================================================================
#  SETTINGS - the only file you ever need to edit
# ============================================================================
#
#  >>> DO NOT PUT API KEYS IN THIS FILE <<<
#
#  Keys go into GitHub's locked box instead. GitHub encrypts them and hides
#  them from everyone, including in logs. Anything typed in this file is
#  plain text that anyone with repo access can read.
#
#  Where:  your repo -> Settings -> Secrets and variables -> Actions
#          -> "New repository secret"
#
#  Add these, with the Name typed EXACTLY as shown:
#
#    Name                   What to paste
#    ---------------------  ----------------------------------------------
#    ANTHROPIC_API_KEY      your Claude key        (starts with sk-ant-)
#    ELEVENLABS_API_KEY     your ElevenLabs key
#    TELEGRAM_BOT_TOKEN     from @BotFather        (looks like 123456:ABC...)
#    TELEGRAM_CHAT_ID       the number from the getUpdates page
#
#    Later, for auto-posting:
#    UPLOAD_POST_API_KEY    from upload-post.com -> API Keys
#    UPLOAD_POST_USER       your Upload-Post profile name
#
#  If one is missing, the run stops and tells you which one.
# ============================================================================


# ---- Voice -----------------------------------------------------------------
# ElevenLabs -> My Voices -> your voice -> ID  (not secret, safe to keep here)
ELEVENLABS_VOICE_ID = "deCz1h6mjB7HnY2xQz08"

# If the Thai sounds wrong, try another model name from ElevenLabs.
ELEVENLABS_MODEL = "eleven_v3"


# ---- Script writing ----------------------------------------------------------
CLAUDE_MODEL = "claude-sonnet-5-5"
WEB_SEARCH_TOOL = "web_search_20250305"

# Who is speaking, so Claude uses the right Thai polite particle:
#   "male"    -> ครับ      "female" -> ค่ะ/คะ      "neutral" -> no ครับ/ค่ะ at all (safe default)
NARRATOR = "neutral"

# Look for scam news from the last N days first (falls back to 14 days if nothing fits)
NEWS_DAYS = 3

# Second Claude pass that fact-checks against the sources and fixes unnatural Thai.
# Costs about +$0.05-0.10 per video. Set False to turn off.
EDITOR_PASS = True


# ---- Video look ----------------------------------------------------------------
# "constructivist" = the red/black/cream poster style (needs the web/ folder)
# "classic"        = the original yellow phone-chat style
# If the constructivist renderer ever fails, that day falls back to classic automatically.
RENDERER = "constructivist"


# ---- Channel -------------------------------------------------------------------
# Shown on the end card: "กดติดตาม <name>  กลโกงใหม่ทุกวัน". Leave "" to hide.
CHANNEL_NAME = "ทันท่วงที"


# ---- How often (sized to stay inside your current plans) -----------------------
# Days that get a new video (Bangkok time). 4 a week = about 17 videos a month,
# which uses about 17k of ElevenLabs Starter's 30k monthly credits.
POST_DAYS = "mon,wed,fri,sun"

# Your ElevenLabs plan's monthly credits. Only used if the API key can't read the
# plan itself - normally the real remaining balance is checked every morning.
VOICE_MONTHLY_CREDITS = 30000
# Credits kept spare for re-runs and the setup check.
VOICE_RESERVE = 2000

# Facebook Reels can't be longer than 90 seconds; longer narration is sped up slightly.
MAX_SECONDS = 88


# ---- Posting -------------------------------------------------------------------
# "auto"    = posts every day by itself (reply "skip" in Telegram to stop that day's post)
# "approve" = posts only after you reply "ok"
POST_MODE = "auto"

# In "auto" mode the video goes out at the first hourly check from this hour (Bangkok),
# about 18:23 - evening is when Thai viewers scroll most. A video that fails the safety
# check (no sources, fact-check didn't run, or the backup look was used) is held, and
# Telegram asks you to reply "ok" instead.
AUTO_POST_HOUR = 18

# Shown in the morning Telegram message as the posting time.
POST_TIME = "18:30"

# Where each video is posted. TikTok needs a paid Upload-Post plan and the TikTok account
# connected to your Upload-Post profile; a platform that isn't connected is simply skipped.
PLATFORMS = "youtube,facebook,instagram,tiktok"

# Marks the AI voice on YouTube/TikTok. Honest and safe; set False to turn off.
LABEL_AI = True
