# Map-explainer style (prototype, not used by the daily pipeline yet)

Storyboard (8 key frames) for a light street-map explainer with an original presenter mascot,
**น้องทัน** (yellow hoodie, red cap with the "!" badge from the logo). Published for review at
https://claude.ai/artifact/Qt2Non17PvSPsxJ63L91aP - **awaiting the owner's approval**.

- `theme.js`   - drawing kit: base map (Natural Earth + province shapes), camera (`camFit`, `camLerp`),
                 pins, danger zones, pills, cards, captions with red key words, the mascot
                 (`mascot(ctx, x, y, scale, pose, mouth, blink)`; poses: wave, point, shock, phone, megaphone, thumb).
- `panels.js`  - renders the 8 storyboard panels to `out/` (run `node design/map-explainer/panels.js`
                 after `npm ci --prefix web`).
- `basemap.json` - Thailand + neighbours: land, provinces (77), highways, rail, rivers, lakes, urban areas,
                 75 towns with Thai names. Source: Natural Earth 1:10m (public domain), simplified.

To ship it: port these functions into a theme for `web/explainer.js` (reuse its beats, timing, word-synced
captions and sound score), select it with `RENDERER = "map"` in settings.py, add mouth movement from the
narration loudness, and keep the classic renderer as the fallback. Limits: no street-level detail or 3D
buildings (those need a paid map licence for a monetised channel).
