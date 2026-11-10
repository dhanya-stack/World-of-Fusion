# Fusion Field Notes

A visually rich, standalone educational website and personal research/news hub for global fusion energy.

## Start using it

- Open **index.html** in your browser to explore all the lessons, animations, projects, glossary and the initial dated news/papers collection.
- The 21-day reading tracker uses your browser's local storage. It stays on that browser and isn't synced across devices.
- The illustrations are simplified, and the hero is a conceptual artwork—not an actual operating machine.

## Set up automatic updates on GitHub Pages

1. Create a new GitHub repository, for example `fusion-field-notes`. Upload the entire package including `.github/workflows/refresh.yml`, `index.html`, `update_feed.py` and `data/feed.json`.
2. In the repository choose **Settings → Pages → Deploy from a branch → main → / (root)**. Save.
3. Under **Settings → Actions → General**, make sure workflow permissions permit reading/writing repository contents (or use a PAT with the minimum necessary scope if required by your organization).
4. Open **Actions → Refresh fusion headlines and papers → Run workflow** once. The included scheduled job then attempts updates twice daily.
5. Share or bookmark the GitHub Pages URL. When accessed via `https://`, the page reads `data/feed.json` and displays newer entries. When opened with `file://`, it shows the embedded starting collection instead.

The update script uses a Google News RSS search and the arXiv metadata API. It retains existing data if both sources fail, and labels automated summaries appropriately. Like any news aggregator, it needs occasional review and can be interrupted by publisher/API changes. Links go to original publishers; it does not scrape full articles.

## Content and attributions

- Animated apparatus diagrams are original schematic SVGs, simplified for teaching.
- Main fusion image is original, AI-generated conceptual artwork; it does **not** depict a real experiment or a real reactor operating.
- The initial news and preprint links point to original sources and are dated 10 November 2026. Facility/project links are intended as a starting directory, not an exhaustive listing or a claim that all listed designs have achieved net electricity.
- Fonts are optionally loaded from Google Fonts; a system-font fallback works offline.

This site is for educational use. Validate all claims, targets and timelines against primary sources before citing them professionally.
