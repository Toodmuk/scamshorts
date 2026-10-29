# Instructions for AI agents working on this repo

1. Read `HANDOFF.md` first - it explains the project, services, secrets, schedule, files and the
   current blocking point (section 8).
2. `settings.py` is the only config file. Never put API keys in code; they are GitHub Actions secrets.
3. Never overwrite `data/` (live state written by the workflows) and never commit `web/node_modules/`.
4. The owner deploys by uploading files in the GitHub web UI. Give complete files or a zip of changed
   files, plus short step-by-step instructions. The posting workflow file in the repo is `post.yaml`.
5. Keep changes simple and inside current plans (no service upgrades). Prefer lowering frequency over
   paying more. Posting is fully automatic; keep the safety hold and the fallbacks working.
6. After changing code: run the silent preview (`python run.py --script samples/sample_script.json --no-voice`),
   syntax-check Python/JS/YAML, and bump `VERSION` + `CHANGELOG.md`.
7. Talk to the owner in short, direct bullets.
