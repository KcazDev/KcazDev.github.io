"# KcazDev.github.io"

## Site organization

- `index.html`: portfolio homepage.
- `projects/<project-slug>/index.html`: project case studies.
- `assets/css/` and `assets/js/`: shared stylesheets and scripts.
- `assets/images/<project-slug>/` and `assets/videos/<project-slug>/`: project media.
- `assets/images/shared/`: media shared across projects or not assigned yet.
- `assets/documents/`: downloadable research papers.
- `games/`: self-contained browser games; keep their internal paths together.
- `docs/notes/`: development notes.

Use lowercase kebab-case for new filenames. Use relative URLs and keep filenames case-correct.
Root case-study HTML files are compatibility redirects; edit the pages under projects.
Do not delete old public URLs without considering existing bookmarks.

Validate: `python tools/migrate_portfolio.py . --validate`
Preview locally: `python -m http.server 8000` then open http://localhost:8000/.
The validator checks static HTML attributes, CSS url() paths, and HTML anchors.
External services and dynamically constructed JavaScript URLs need browser testing.
