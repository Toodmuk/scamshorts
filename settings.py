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


# ---- Posting (used after you set up Upload-Post) -----------------------------
# "approve" = posts only after you reply ok in Telegram
# "auto"    = posts unless you reply skip
POST_MODE = "approve"

# Shown in the Telegram message. The real posting time is the cron line in
# .github/workflows/post.yml  ("0 11 * * *" = 18:00 Bangkok)
POST_TIME = "18:00"

# Add ",tiktok" if you're on a paid Upload-Post plan
PLATFORMS = "youtube,facebook,instagram"

# Marks the AI voice on YouTube/TikTok. Honest and safe; set False to turn off.
LABEL_AI = True
