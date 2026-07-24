# GitVisuals - Complete Usage Guide

> Flatten any GitHub repository into a beautiful, interactive static HTML page

**Repository:** https://github.com/xelphh/GitVisuals.git

---

## Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/xelphh/GitVisuals.git
cd GitVisuals

# Install dependencies
pip install -r requirements.txt

# Run it!
python GitVisuals.py https://github.com/username/repo
```

### Using with uv

```bash
uv pip install -r requirements.txt
python GitVisuals.py https://github.com/username/repo
```

---

## Usage

### Basic Command

```bash
python GitVisuals.py <GITHUB_URL>
```

**Example:**
```bash
python GitVisuals.py https://github.com/torvalds/linux
```

This will:
1. 📥 Clone the repo to a temporary directory
2. 🔍 Scan all files
3. 🎨 Generate beautiful HTML with syntax highlighting
4. 💾 Save to temp directory
5. 🌐 **Automatically open in your browser**

---

## Command Options

### `--no-open`
Don't automatically open the HTML in browser (just generate the file)

```bash
python GitVisuals.py https://github.com/username/repo --no-open
```

### `-o` or `--out`
Specify custom output path for the HTML file

```bash
python GitVisuals.py https://github.com/username/repo -o ~/Desktop/myrepo.html
```

### `--max-bytes`
Set maximum file size to include (default: 50 KiB = 51,200 bytes)

```bash
# Include files up to 100 KiB
python GitVisuals.py https://github.com/username/repo --max-bytes 102400
```

---

## Usage Examples

### Example 1: Generate and save locally
```bash
python GitVisuals.py https://github.com/facebook/react -o react.html
```

### Example 2: Large repository with custom file size limit
```bash
python GitVisuals.py https://github.com/torvalds/linux --max-bytes 200000 --no-open -o linux.html
```

### Example 3: Quick preview without saving
```bash
python GitVisuals.py https://github.com/python/cpython
```

---

## Features

### 📁 VS Code-Style File Explorer
- Expandable/collapsible folder tree in the sidebar
- Matches VS Code's familiar UI/UX
- Clean hierarchical file organization
- Root files clearly separated from directories

### 🔍 File Search & Filter
- Real-time file search in the sidebar
- Quickly navigate large repositories
- Filter both sidebar and main content area
- Matches files as you type

### 💻 Dual View Modes

#### Editor View (Default)
- Beautiful dark theme with modern colors
- Syntax highlighting for all code files via Pygments
- Line numbers for every code file
- Markdown rendering for README and documentation
- Sticky file headers while scrolling
- Directory tree visualization
- Repository metadata (URL & commit hash)

#### LLM View (CXML Format)
- Raw text format ready for AI analysis
- Perfect for pasting into Claude, ChatGPT, or other LLMs
- One-click "copy all" button
- Includes all renderable files with proper formatting

### ✨ Code Display
- **Syntax highlighting** via Pygments for 500+ languages
- **Line numbers** for easy reference
- **Copy buttons** - one-click copy for entire files
- **Markdown rendering** for .md files with proper formatting
- **Automatic language detection** based on file extension

### 🎨 Modern UI
- **Dark theme** using Oklahoma Lch color model
- Better contrast and readability
- Smooth transitions and animations
- Responsive design
- Native monospace font stacks

### 📊 Smart File Filtering
- Automatically skips binary files (.png, .jpg, .pdf, .zip, etc.)
- Filters out oversized files (configurable with `--max-bytes`)
- Ignores .git folders
- Shows skip statistics in sidebar

### 📐 Repository Information
- Display GitHub URL in header and footer
- Show current commit hash (shortened)
- File statistics (rendered count, total size, file count)
- Skip summary (binary files, large files, ignored)

---

## Output

The generated HTML file is **completely standalone**:
- ✅ No external dependencies
- ✅ No API calls needed
- ✅ Works offline
- ✅ Can be shared via email or downloaded
- ✅ Opens in any modern browser

### File Size
Output HTML is typically:
- Small repos (< 100 files): 500 KB - 2 MB
- Medium repos (100-500 files): 2-10 MB
- Large repos: 10-50+ MB (depending on code volume)

---

## Default Behavior

| Setting | Default | How to Change |
|---------|---------|---------------|
| Output location | System temp directory | Use `-o` flag |
| Auto-open browser | ✅ Yes | Use `--no-open` flag |
| Max file size | 50 KiB | Use `--max-bytes` flag |
| Include binaries | ❌ No | Can't be changed (by design) |

---

## What Gets Included

✅ **Included:**
- All source code files (.py, .js, .go, .rs, .c, etc.)
- Markdown files (.md, .markdown, .mdown)
- Configuration files (.json, .yaml, .toml, .xml, etc.)
- Text files (.txt, .log, .csv)
- LICENSE and other docs

❌ **Excluded:**
- Binary files (.png, .jpg, .pdf, .zip, .so, .dll, etc.)
- Files exceeding `--max-bytes` limit
- Git internals (.git folder)
- Files larger than configured limit

---

## Limitations

- **One-way tool**: Reads repos, doesn't write back to GitHub
- **Shallow clone**: Uses `--depth 1` for speed (gets latest commit only)
- **No Git history**: Only includes current state, not history
- **Static output**: Generated HTML doesn't update if repo changes
- **Temporary deletion**: Local clone is deleted after HTML generation (GitHub repo stays untouched)

---

## Requirements

- Python 3.7+
- `pygments` - Syntax highlighting
- `markdown` - Markdown rendering
- `git` - For cloning repositories

Install all dependencies with:
```bash
pip install -r requirements.txt
```

---

## Examples by Use Case

### Code Review
```bash
python GitVisuals.py https://github.com/username/pull-request-repo -o review.html
```
Perfect for reviewing entire codebases in one view.

### Learning
```bash
python GitVisuals.py https://github.com/torvalds/linux --no-open -o linux-kernel.html
```
Study real-world code with Ctrl+F search.

### AI Analysis
```bash
python GitVisuals.py https://github.com/openai/whisper
```
Switch to LLM view and paste into Claude for code analysis.

### Documentation
```bash
python GitVisuals.py https://github.com/username/mylib -o mylib-docs.html
```
Share a snapshot of your library's code and docs.

---

## Tips & Tricks

1. **Use Ctrl+F** in the generated HTML for instant code search
2. **Expand folders** in the sidebar to see directory structure
3. **Click file names** in sidebar to jump to that file
4. **Copy code** with the copy button for each file
5. **Switch views** between Editor and LLM for different use cases
6. **Filter files** in sidebar search to focus on specific code

---

## License

0BSD - Do whatever you want with it

---

## Repository

Source code: https://github.com/xelphh/GitVisuals.git
