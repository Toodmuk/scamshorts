# ทันท่วงที — revision history

## r9 · 26 Oct 2026 (this bundle)
- Fix for "no JSON object in model output" / "Expecting ',' delimiter": Claude now hands the script
  back through a structured tool call (always valid JSON) instead of writing JSON as text.
- Backup: if it ever writes JSON as text anyway, common slips (e.g. a quote inside Thai text) are
  repaired automatically; if the output is unusable it is asked again (up to 3 tries).
- More room for longer 60-80 s scripts (max_tokens 8000).

## r8 · 26 Oct 2026
- TikTok added to `PLATFORMS` (needs a paid Upload-Post plan and TikTok connected to profile tuntuangtee).
- A platform that isn't connected yet is reported as SKIPPED, not as an error.
- TikTok daily-cap fallback (video lands in TikTok drafts) is flagged in Telegram.
- "โพสต์แล้ว" message now shows Upload-Post's monthly usage (e.g. 12/100).

## r7 · 26 Oct 2026
- Posts 4 days a week (Mon, Wed, Fri, Sun) to stay inside current plans; change `POST_DAYS` in settings.py.
- Voice credits are checked every posting morning; scripts are sized to last until the plan renews,
  and a day is skipped with a Telegram note only if credits are really short.
- Videos capped at 88 s (Facebook Reels limit 90 s).
- Posting checks 5 a day (12:23, 18:23–21:23); videos kept 3 days.

## r6
- Fully automatic posting at ~18:23 with a safety hold (no sources / no fact-check / backup look).
- Weekly Telegram report (Mondays 09:17) with Claude's analysis; lessons fed back into scripts.
- 60–80 s documentary-style scripts; camera motion; compare, bars and percent charts.

## r5
- Constructivist video style (Node renderer) with automatic fallback to the classic look.
