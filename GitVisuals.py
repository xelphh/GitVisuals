#!/usr/bin/env python3
"""
Flatten a GitHub repo into a single HTML page with guitocopy-style UI.
"""

from __future__ import annotations
import argparse
import html
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from dataclasses import dataclass
from typing import List

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename, TextLexer
import markdown

MAX_DEFAULT_BYTES = 50 * 1024
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".mp3", ".mp4", ".mov", ".avi", ".mkv", ".wav", ".ogg", ".flac",
    ".ttf", ".otf", ".eot", ".woff", ".woff2",
    ".so", ".dll", ".dylib", ".class", ".jar", ".exe", ".bin",
}
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".mkdn"}

@dataclass
class RenderDecision:
    include: bool
    reason: str

@dataclass
class FileInfo:
    path: pathlib.Path
    rel: str
    size: int
    decision: RenderDecision


def run(cmd: List[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def git_clone(url: str, dst: str) -> None:
    run(["git", "clone", "--depth", "1", url, dst])


def git_head_commit(repo_dir: str) -> str:
    try:
        cp = run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
        return cp.stdout.strip()
    except Exception:
        return "(unknown)"


def bytes_human(n: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    f = float(n)
    i = 0
    while f >= 1024.0 and i < len(units) - 1:
        f /= 1024.0
        i += 1
    if i == 0:
        return f"{int(f)} {units[i]}"
    else:
        return f"{f:.1f} {units[i]}"


def looks_binary(path: pathlib.Path) -> bool:
    ext = path.suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return True
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
        if b"\x00" in chunk:
            return True
        try:
            chunk.decode("utf-8")
        except UnicodeDecodeError:
            return True
        return False
    except Exception:
        return True


def decide_file(path: pathlib.Path, repo_root: pathlib.Path, max_bytes: int) -> FileInfo:
    rel = str(path.relative_to(repo_root)).replace(os.sep, "/")
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        size = 0
    if "/.git/" in f"/{rel}/" or rel.startswith(".git/"):
        return FileInfo(path, rel, size, RenderDecision(False, "ignored"))
    if size > max_bytes:
        return FileInfo(path, rel, size, RenderDecision(False, "too_large"))
    if looks_binary(path):
        return FileInfo(path, rel, size, RenderDecision(False, "binary"))
    return FileInfo(path, rel, size, RenderDecision(True, "ok"))


def collect_files(repo_root: pathlib.Path, max_bytes: int) -> List[FileInfo]:
    infos: List[FileInfo] = []
    for p in sorted(repo_root.rglob("*")):
        if p.is_symlink():
            continue
        if p.is_file():
            infos.append(decide_file(p, repo_root, max_bytes))
    return infos


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def render_markdown_text(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=["fenced_code", "tables", "toc"])


def highlight_code(text: str, filename: str, formatter: HtmlFormatter) -> str:
    try:
        lexer = get_lexer_for_filename(filename, stripall=False)
    except Exception:
        lexer = TextLexer(stripall=False)
    return highlight(text, lexer, formatter)


def generate_cxml_text(infos: List[FileInfo], repo_dir: pathlib.Path) -> str:
    lines = ["<documents>"]
    rendered = [i for i in infos if i.decision.include]
    for index, i in enumerate(rendered, 1):
        lines.append(f'<document index="{index}">')
        lines.append(f"<source>{i.rel}</source>")
        lines.append("<document_content>")
        try:
            text = read_text(i.path)
            lines.append(text)
        except Exception as e:
            lines.append(f"Failed to read: {str(e)}")
        lines.append("</document_content>")
        lines.append("</document>")
    lines.append("</documents>")
    return "\n".join(lines)


def build_tree_html(repo_dir: pathlib.Path, infos: List[FileInfo]) -> str:
    """Generate file tree HTML with collapsible folders."""
    rendered = [i for i in infos if i.decision.include]
    paths = sorted([i.rel for i in rendered])

    if not paths:
        return ""

    lines = [f"<details class='tree-section'><summary>Directory tree</summary><pre>"]

    root = {}
    for p in paths:
        parts = p.split("/")
        node = root
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]

    def walk(node, prefix=""):
        result = []
        for name in sorted(node.keys()):
            is_last = name == sorted(node.keys())[-1]
            result.append(prefix + ("└── " if is_last else "├── ") + name)
            if node[name]:
                ext = "    " if is_last else "│   "
                result.extend(walk(node[name], prefix + ext))
        return result

    tree_lines = [repo_dir.name] + walk(root, "")
    lines.append(html.escape("\n".join(tree_lines)))
    lines.append("</pre></details>")
    return "\n".join(lines)


def build_html(repo_url: str, repo_dir: pathlib.Path, head_commit: str, infos: List[FileInfo]) -> str:
    formatter = HtmlFormatter(nowrap=False, style='native')
    pygments_css = formatter.get_style_defs('.highlight')

    rendered = [i for i in infos if i.decision.include]
    skipped_binary = len([i for i in infos if i.decision.reason == "binary"])
    skipped_large = len([i for i in infos if i.decision.reason == "too_large"])
    skipped_ignored = len([i for i in infos if i.decision.reason == "ignored"])
    total_files = len(infos)

    repo_name = repo_dir.name

    # Build file tree
    tree_html = build_tree_html(repo_dir, infos)

    # Generate CXML
    cxml_text = generate_cxml_text(infos, repo_dir)

    # Build file sections
    sections_html = []
    for i in rendered:
        p = i.path
        ext = p.suffix.lower()
        anchor = i.rel.replace("/", "-").replace(".", "-")

        try:
            text = read_text(p)
            line_count = text.count("\n") + 1

            if ext in MARKDOWN_EXTENSIONS:
                body_html = render_markdown_text(text)
                is_markdown = True
            else:
                code_html = highlight_code(text, i.rel, formatter)
                line_numbers = "\n".join(str(n) for n in range(1, line_count + 1))
                body_html = f'<div class="code-display"><pre class="line-numbers">{html.escape(line_numbers)}</pre><pre class="code-content">{code_html}</pre></div>'
                is_markdown = False
        except Exception as e:
            body_html = f'<pre class="error">Failed to render: {html.escape(str(e))}</pre>'
            is_markdown = False

        section = f'''
<section class="file-section" id="file-{anchor}">
  <div class="file-header">
    <div>
      <div class="file-path">{html.escape(i.rel)} <span class="file-size">({bytes_human(i.size)})</span></div>
    </div>
    <button class="copy-btn" onclick="copyFileContent('{anchor}')" title="Copy content">copy</button>
  </div>
  <div class="file-body" id="content-{anchor}">
    {body_html if is_markdown else body_html}
  </div>
</section>
'''
        sections_html.append(section)

    # Build file tree sidebar with expandable folders (VS Code style)
    tree_items_html = []
    file_list = sorted([(i.rel, i.path) for i in rendered])

    # Build complete tree structure
    tree = {}
    for rel_path, _ in file_list:
        parts = rel_path.split("/")
        node = tree
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]
        if "__files__" not in node:
            node["__files__"] = []
        node["__files__"].append(rel_path)

    def build_tree_items(node, depth=0, parent_path=""):
        items = []
        folders = sorted([k for k in node.keys() if k != "__files__"])
        files = sorted(node.get("__files__", []))

        # Add folders first (expandable)
        for folder in folders:
            folder_id = f"folder-{parent_path}{folder}".replace("/", "-")
            items.append(f'<div class="file-tree-item is-folder" data-folder="{folder_id}" onclick="toggleFolder(event)" style="padding-left:{10 + depth*14}px;"><span class="tree-icon expand-icon">▶</span><span class="folder-name">📁 {html.escape(folder)}</span></div>')
            items.append(f'<div class="folder-contents" id="{folder_id}" style="display:none;">')
            items.extend(build_tree_items(node[folder], depth + 1, f"{parent_path}{folder}/"))
            items.append('</div>')

        # Add files
        for rel_path in files:
            anchor = rel_path.replace("/", "-").replace(".", "-")
            file_name = rel_path.split("/")[-1]
            items.append(f'<div class="file-tree-item is-file" style="padding-left:{10 + (depth+1)*14}px;"><span class="tree-icon">·</span><a href="#file-{anchor}">{html.escape(file_name)}</a></div>')

        return items

    tree_items_html.extend(build_tree_items(tree))

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>repo/flatten – {html.escape(repo_url)}</title>
<style>
  @font-face {{ font-family: 'system-mono'; src: local('SF Mono'); }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: oklch(16% 0.012 260); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px; color: oklch(87% 0.01 260); }}
  ::selection {{ background: oklch(45% 0.14 85 / 0.35); }}
  ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
  ::-webkit-scrollbar-thumb {{ background: oklch(30% 0.014 260); border-radius: 6px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}

  .viewport {{ height: 100vh; display: flex; flex-direction: column; }}

  /* Header */
  .header {{ display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid oklch(28% 0.012 260); background: oklch(18.5% 0.013 260); flex-shrink: 0; }}
  .header-brand {{ display: flex; align-items: center; gap: 8px; color: oklch(75% 0.15 85); font-weight: 700; letter-spacing: 0.3px; font-size: 15px; }}
  .header-divider {{ width: 1px; height: 20px; background: oklch(28% 0.012 260); }}
  .header-info {{ flex: 1; color: oklch(60% 0.01 260); font-size: 12px; }}
  .header-actions {{ display: flex; gap: 6px; }}

  .toggle-group {{ display: flex; gap: 6px; border: 1px solid oklch(30% 0.014 260); border-radius: 5px; overflow: hidden; }}
  .toggle-btn {{ border: none; font-family: inherit; font-size: 12px; padding: 6px 12px; cursor: pointer; transition: all 0.2s; background: transparent; color: oklch(60% 0.01 260); }}
  .toggle-btn.active {{ background: oklch(75% 0.15 85); color: oklch(18% 0.02 85); }}
  .toggle-btn:not(.active):hover {{ color: oklch(80% 0.01 260); }}
  .toggle-btn:not(.active) {{ border-right: 1px solid oklch(30% 0.014 260); }}
  .toggle-btn:last-child:not(.active) {{ border-right: none; }}

  /* Main layout */
  .main {{ display: flex; flex: 1; min-height: 0; }}

  /* Sidebar */
  .sidebar {{ width: 280px; flex-shrink: 0; border-right: 1px solid oklch(28% 0.012 260); background: oklch(17.5% 0.012 260); overflow-y: auto; padding: 10px 0; }}
  .sidebar-search {{ padding: 0 10px 8px 10px; }}
  .sidebar-search input {{ width: 100%; box-sizing: border-box; background: oklch(14% 0.012 260); border: 1px solid oklch(28% 0.012 260); color: oklch(80% 0.01 260); font-family: inherit; font-size: 12px; padding: 6px 8px; border-radius: 4px; outline: none; }}
  .sidebar-search input:focus {{ border-color: oklch(60% 0.13 200); }}
  .sidebar-label {{ padding: 2px 12px 8px 12px; color: oklch(55% 0.01 260); font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; }}
  .file-tree-item {{ display: flex; align-items: center; gap: 6px; padding: 3px 6px; cursor: pointer; color: oklch(78% 0.01 260); font-size: 12.5px; user-select: none; }}
  .file-tree-item:hover {{ background: oklch(22% 0.013 260); border-radius: 4px; }}
  .file-tree-item.is-folder {{ color: oklch(80% 0.01 260); }}
  .file-tree-item.is-file {{ color: oklch(75% 0.01 260); }}
  .expand-icon {{ width: 14px; display: inline-flex; align-items: center; justify-content: center; font-size: 9px; transition: transform 0.2s; }}
  .file-tree-item.is-folder[data-expanded="true"] .expand-icon {{ transform: rotate(90deg); }}
  .folder-contents {{ margin-left: 0; }}
  .file-tree-item a {{ text-decoration: none; color: inherit; display: flex; align-items: center; gap: 6px; width: 100%; word-break: break-all; }}
  .file-tree-item a:hover {{ color: oklch(60% 0.13 200); }}
  .tree-icon {{ width: 12px; display: inline-block; color: oklch(55% 0.01 260); }}

  /* Content area */
  .content {{ flex: 1; overflow-y: auto; min-width: 0; background: oklch(15.5% 0.012 260); }}

  /* File section */
  .file-section {{ border-bottom: 1px solid oklch(26% 0.012 260); }}
  .file-header {{ position: sticky; top: 0; z-index: 2; display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 16px; background: oklch(19% 0.013 260); border-bottom: 1px solid oklch(28% 0.012 260); }}
  .file-path {{ color: oklch(85% 0.01 260); font-size: 12.5px; word-break: break-all; }}
  .file-size {{ color: oklch(50% 0.01 260); }}
  .copy-btn {{ flex-shrink: 0; background: transparent; border: 1px solid oklch(32% 0.014 260); color: oklch(65% 0.01 260); font-family: inherit; font-size: 11px; padding: 4px 9px; border-radius: 4px; cursor: pointer; transition: all 0.2s; }}
  .copy-btn:hover {{ border-color: oklch(60% 0.13 200); color: oklch(80% 0.01 260); }}
  .copy-btn.copied {{ background: oklch(45% 0.10 130); border-color: oklch(65% 0.10 130); color: oklch(90% 0.01 130); }}

  /* Code display */
  .code-display {{ display: flex; padding: 10px 0; }}
  .line-numbers {{ margin: 0; padding: 0 12px; text-align: right; color: oklch(38% 0.012 260); user-select: none; line-height: 1.6; font-size: 12.5px; flex-shrink: 0; }}
  .code-content {{ margin: 0; padding: 0 16px 0 8px; overflow-x: auto; color: oklch(83% 0.01 260); line-height: 1.6; font-size: 12.5px; flex: 1; }}

  /* Tree section */
  .tree-section {{ margin: 14px 16px; border: 1px solid oklch(28% 0.012 260); border-radius: 6px; background: oklch(17.5% 0.012 260); }}
  .tree-section summary {{ padding: 8px 12px; cursor: pointer; color: oklch(65% 0.01 260); font-size: 12.5px; user-select: none; }}
  .tree-section pre {{ margin: 0; padding: 12px 16px; overflow-x: auto; color: oklch(78% 0.01 260); font-size: 12px; line-height: 1.5; background: transparent; border: none; }}

  /* LLM view */
  .llm-view {{ display: none; padding: 16px; }}
  .llm-view.active {{ display: block; }}
  .llm-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
  .llm-header > div {{ color: oklch(60% 0.01 260); font-size: 12.5px; }}
  .llm-text {{ width: 100%; height: 70vh; font-family: inherit; font-size: 12px; border: 1px solid oklch(28% 0.012 260); border-radius: 6px; padding: 14px; background: oklch(14% 0.012 260); color: oklch(80% 0.01 260); resize: vertical; white-space: pre-wrap; word-break: break-all; line-height: 1.5; }}

  /* Footer */
  .footer {{ flex-shrink: 0; display: flex; align-items: center; gap: 16px; padding: 5px 14px; background: oklch(20% 0.03 250); border-top: 1px solid oklch(28% 0.012 260); font-size: 11.5px; color: oklch(75% 0.02 250); }}

  {pygments_css}
</style>
</head>
<body>
<div class="viewport">
  <div class="header">
    <div class="header-brand">⌥ repo/flatten</div>
    <div class="header-divider"></div>
    <div class="header-info">{html.escape(repo_url)} @ {html.escape(head_commit[:8])}</div>
    <div class="header-actions">
      <div class="toggle-group">
        <button class="toggle-btn active" onclick="showEditorView()">Editor</button>
        <button class="toggle-btn" onclick="showLLMView()">LLM / CXML</button>
      </div>
    </div>
  </div>

  <div class="main">
    <nav class="sidebar">
      <div class="sidebar-search">
        <input type="text" id="file-search" placeholder="filter files…" onkeyup="filterFiles()" autocomplete="off" />
      </div>
      <div class="sidebar-label">{len(rendered)} files rendered</div>
      <div id="file-tree">
        {chr(10).join(tree_items_html)}
      </div>
      <div style="padding:8px 12px; border-top:1px solid oklch(26% 0.012 260); color:oklch(50% 0.01 260); font-size:11.5px; line-height:1.6; margin-top:10px;">
        Skipped: {skipped_binary} binary, {skipped_large} large, {skipped_ignored} ignored
      </div>
    </nav>

    <main class="content">
      <div id="editor-view" class="active">
        {tree_html}
        {chr(10).join(sections_html)}
      </div>

      <div id="llm-view" class="llm-view">
        <div class="llm-header">
          <div>CXML — paste this into an LLM</div>
          <button class="copy-btn" onclick="copyAllCxml()">copy all</button>
        </div>
        <pre class="llm-text" id="llm-text">{html.escape(cxml_text)}</pre>
      </div>
    </main>
  </div>

  <div class="footer">
    <span>{repo_url}</span>
    <span>commit: {html.escape(head_commit[:8])}</span>
    <span>{len(rendered)} rendered · {bytes_human(sum(i.size for i in rendered))} · {total_files} total</span>
  </div>
</div>

<script>
function toggleFolder(event) {{
  event.preventDefault();
  event.stopPropagation();
  const folder = event.currentTarget;
  const folderId = folder.getAttribute('data-folder');
  const contents = document.getElementById(folderId);
  const isExpanded = folder.getAttribute('data-expanded') === 'true';

  if (isExpanded) {{
    contents.style.display = 'none';
    folder.setAttribute('data-expanded', 'false');
  }} else {{
    contents.style.display = 'block';
    folder.setAttribute('data-expanded', 'true');
  }}
}}

function showEditorView() {{
  document.getElementById('editor-view').style.display = 'block';
  document.getElementById('llm-view').classList.remove('active');
  document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}}

function showLLMView() {{
  document.getElementById('editor-view').style.display = 'none';
  document.getElementById('llm-view').classList.add('active');
  document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}}

function copyFileContent(anchor) {{
  const content = document.getElementById('content-' + anchor);
  navigator.clipboard.writeText(content.innerText).then(() => {{
    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = 'copied';
    btn.classList.add('copied');
    setTimeout(() => {{
      btn.textContent = orig;
      btn.classList.remove('copied');
    }}, 1500);
  }});
}}

function copyAllCxml() {{
  const text = document.getElementById('llm-text').textContent;
  navigator.clipboard.writeText(text).then(() => {{
    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = 'copied';
    btn.classList.add('copied');
    setTimeout(() => {{
      btn.textContent = orig;
      btn.classList.remove('copied');
    }}, 1500);
  }});
}}

function filterFiles() {{
  const query = document.getElementById('file-search').value.toLowerCase();
  const items = document.querySelectorAll('.file-tree-item');
  const sections = document.querySelectorAll('.file-section');

  items.forEach(item => {{
    const text = item.textContent.toLowerCase();
    item.style.display = query && !text.includes(query) ? 'none' : 'flex';
  }});

  sections.forEach(sec => {{
    const path = sec.querySelector('.file-path').textContent.toLowerCase();
    sec.style.display = query && !path.includes(query) ? 'none' : 'block';
  }});
}}
</script>
</body>
</html>
'''


def derive_temp_output_path(repo_url: str) -> pathlib.Path:
    parts = repo_url.rstrip('/').split('/')
    if len(parts) >= 2:
        repo_name = parts[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        filename = f"{repo_name}.html"
    else:
        filename = "repo.html"
    return pathlib.Path(tempfile.gettempdir()) / filename


def main() -> int:
    ap = argparse.ArgumentParser(description="Flatten a GitHub repo to HTML (guitocopy style)")
    ap.add_argument("repo_url", help="GitHub repo URL")
    ap.add_argument("-o", "--out", help="Output HTML file path")
    ap.add_argument("--max-bytes", type=int, default=MAX_DEFAULT_BYTES, help="Max file size (bytes)")
    ap.add_argument("--no-open", action="store_true", help="Don't open in browser")
    args = ap.parse_args()

    if args.out is None:
        args.out = str(derive_temp_output_path(args.repo_url))

    tmpdir = tempfile.mkdtemp(prefix="flatten_repo_")
    repo_dir = pathlib.Path(tmpdir, "repo")

    try:
        print(f"📁 Cloning {args.repo_url}...", file=sys.stderr)
        git_clone(args.repo_url, str(repo_dir))
        head = git_head_commit(str(repo_dir))
        print(f"✓ Clone complete", file=sys.stderr)

        print(f"📊 Scanning files...", file=sys.stderr)
        infos = collect_files(repo_dir, args.max_bytes)
        rendered_count = sum(1 for i in infos if i.decision.include)
        print(f"✓ Found {len(infos)} files ({rendered_count} rendered)", file=sys.stderr)

        print(f"🔨 Generating HTML...", file=sys.stderr)
        html_out = build_html(args.repo_url, repo_dir, head, infos)

        out_path = pathlib.Path(args.out)
        print(f"💾 Writing to {out_path.resolve()}", file=sys.stderr)
        out_path.write_text(html_out, encoding="utf-8")
        file_size = out_path.stat().st_size
        print(f"✓ Wrote {bytes_human(file_size)}", file=sys.stderr)

        if not args.no_open:
            print(f"🌐 Opening in browser...", file=sys.stderr)
            webbrowser.open(f"file://{out_path.resolve()}")

        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
