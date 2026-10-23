"""Run with Python 3. Default: preview. --apply: backup, migrate, validate.
No dependencies. No commit or push. --validate checks an existing migrated tree.
"""
import argparse, datetime, html, json, os, posixpath, re, shutil, subprocess
from pathlib import Path
from urllib.parse import unquote, quote, urlsplit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('repo', type=Path)
parser.add_argument('--apply', action='store_true')
parser.add_argument('--validate', action='store_true')
args = parser.parse_args()
root = args.repo.resolve()
def git(*argv):
    return subprocess.check_output(['git', '-C', str(root), *argv], text=True).strip()
assert Path(git('rev-parse', '--show-toplevel')).resolve() == root, 'Pass the repository root'
files = {p.relative_to(root).as_posix(): p for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}
attr = re.compile(r'''\b(?:href|src|poster|action|data-src)\s*=\s*(["'])(.*?)\1''', re.I | re.S)
css = re.compile(r'''url\(\s*(["']?)(.*?)\1\s*\)''', re.I)
def target(source, value):
    value = html.unescape(value.strip())
    if not value or value.startswith('//') or urlsplit(value).scheme: return None
    path = unquote(urlsplit(value).path)
    return posixpath.normpath(path.lstrip('/') if path.startswith('/') else posixpath.join(posixpath.dirname(source), path)) if path else source
def refs(name, text):
    if name.endswith('.html'): yield from attr.finditer(text)
    if name.endswith(('.html', '.css')): yield from css.finditer(text)
def validate(tree):
    errors, count = [], 0
    for name, data in tree.items():
        if not name.endswith(('.html', '.css')): continue
        text = data.decode('utf-8-sig')
        for m in refs(name, text):
            dest = target(name, m.group(2))
            if dest is None: continue
            count += 1
            if dest not in tree and dest.rstrip('/') + '/index.html' not in tree:
                errors.append(f'{name}: {m.group(2)} -> {dest}')
            fragment = unquote(urlsplit(html.unescape(m.group(2))).fragment)
            resolved = dest if dest in tree else dest.rstrip('/') + '/index.html'
            if fragment and resolved.endswith('.html') and resolved in tree:
                body = tree[resolved].decode('utf-8-sig')
                ids = re.findall(r'''\b(?:id|name)\s*=\s*["']([^"']+)["']''', body)
                if fragment not in ids: errors.append(f'{name}: missing anchor {m.group(2)}')
    return count, errors
if args.validate:
    count, errors = validate({n: p.read_bytes() for n, p in files.items()})
    print(json.dumps({'references': count, 'errors': errors}, indent=2))
    raise SystemExit(bool(errors))
assert not git('status', '--porcelain', '--untracked-files=all'), 'Commit or stash existing changes first'
pages = {'contractor_website':'contractor-ai','hunter-system':'hunter-system','knights_adventure':'knights-adventure','original_artwork':'original-artwork','pirate_frenzy':'pirate-frenzy','quantum_circus':'quantum-circus','UI_UX_app':'ui-ux-app','unreal_environment':'unreal-environment'}
mapping = {n: n for n in files}
owners = {}
for stem, slug in pages.items():
    name = stem + '.html'
    assert name in files, f'Missing expected page: {name}'
    mapping[name] = f'projects/{slug}/index.html'
    for m in refs(name, files[name].read_text(encoding='utf-8-sig')):
        dest = target(name, m.group(2))
        if dest and dest.startswith('assets/'): owners.setdefault(dest, set()).add(slug)
for name in files:
    p = Path(name)
    if '/' not in name and p.suffix == '.css': mapping[name] = 'assets/css/' + name
    elif '/' not in name and p.suffix == '.js': mapping[name] = 'assets/js/' + name
    elif '/' not in name and p.suffix.lower() == '.pdf': mapping[name] = 'assets/documents/' + name
    elif name == 'webpage test.txt': mapping[name] = 'docs/notes/webpage-test.txt'
    elif name.startswith('assets/') and len(p.parts) == 2:
        group = next(iter(owners[name])) if len(owners.get(name, set())) == 1 else 'shared'
        kind = 'videos' if p.suffix.lower() in {'.mp4','.webm','.mov'} else 'images'
        clean = re.sub(r'[^a-z0-9.]+', '-', p.name.lower()).strip('-')
        mapping[name] = f'assets/{kind}/{group}/{clean}'
assert len(set(mapping.values())) == len(mapping), 'Destination collision'
assert any(k != v for k, v in mapping.items()), 'Already migrated'
tree = {}
for old, path in files.items():
    new = mapping[old]
    data = path.read_bytes()
    if old.endswith(('.html','.css')):
        text = data.decode('utf-8-sig')
        def replace(m):
            value = m.group(2)
            dest = target(old, value)
            if dest not in mapping: return m.group(0)
            parsed = urlsplit(html.unescape(value))
            if not parsed.path and new == mapping[dest]: return m.group(0)
            rel = posixpath.relpath(mapping[dest], posixpath.dirname(new) or '.')
            updated = quote(rel, safe='/-._~')
            if parsed.query: updated += '?' + parsed.query
            if parsed.fragment: updated += '#' + parsed.fragment
            return m.group(0)[:m.start(2)-m.start()] + updated + m.group(0)[m.end(2)-m.start():]
        text = attr.sub(replace, text) if old.endswith('.html') else text
        text = css.sub(replace, text)
        data = text.encode('utf-8')
    tree[new] = data
for stem, slug in pages.items():
    dest = f'projects/{slug}/index.html'
    tree[stem+'.html'] = (f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Page moved</title><meta http-equiv="refresh" content="0;url={dest}"><link rel="canonical" href="{dest}"><a href="{dest}">Continue to project</a><script>location.replace("{dest}"+location.search+location.hash)</script></html>\n').encode()
guide = '''\n\n## Site organization\n\n- `index.html`: portfolio homepage.\n- `projects/<project-slug>/index.html`: project case studies.\n- `assets/css/` and `assets/js/`: shared stylesheets and scripts.\n- `assets/images/<project-slug>/` and `assets/videos/<project-slug>/`: project media.\n- `assets/images/shared/`: media shared across projects or not assigned yet.\n- `assets/documents/`: downloadable research papers.\n- `games/`: self-contained browser games; keep their internal paths together.\n- `docs/notes/`: development notes.\n\nUse lowercase kebab-case for new filenames. Use relative URLs and keep filenames case-correct.\nRoot case-study HTML files are compatibility redirects; edit the pages under projects.\nDo not delete old public URLs without considering existing bookmarks.\n\nValidate: `python tools/migrate_portfolio.py . --validate`\nPreview locally: `python -m http.server 8000` then open http://localhost:8000/.\nThe validator checks static HTML attributes, CSS url() paths, and HTML anchors.\nExternal services and dynamically constructed JavaScript URLs need browser testing.\n'''
tree['README.md'] = tree.get('README.md', b'').rstrip() + guide.encode()
tree['tools/migrate_portfolio.py'] = Path(__file__).read_bytes()
count, errors = validate(tree)
report = {'moves': {k:v for k,v in mapping.items() if k != v}, 'references':count, 'errors':errors}
print(json.dumps(report, indent=2))
assert not errors, 'Migration aborted before writes: resolve reported references'
if not args.apply: raise SystemExit(0)
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup = root.parent / (root.name + '-backup-' + stamp)
shutil.copytree(root, backup)
assert (backup / '.git').is_dir(), 'Backup must include Git history'
branch = 'backup/organization-' + stamp
git('branch', branch)
git('switch', '-c', 'chore/organize-portfolio-' + stamp)
# Move only mapped files; paths are validated to remain inside this repository.
for old, new in mapping.items():
    if old == new: continue
    source, dest = root / old, root / new
    assert source.resolve().is_relative_to(root) and dest.resolve().is_relative_to(root)
    assert not dest.exists(), f'Destination exists: {dest}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
for name, data in tree.items():
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data: path.write_bytes(data)
actual = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}
count, errors = validate(actual)
report.update(backup=str(backup), backup_branch=branch, working_branch=git('branch','--show-current'), references=count, errors=errors)
(root / 'docs' / 'migration-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k != 'moves'}, indent=2))
assert not errors, f'Validation failed. Full backup: {backup}'
