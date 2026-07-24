# GitVisuals

Flatten any GitHub repository into a single HTML page.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python GitVisuals.py https://github.com/username/repo
```

This clones the repo, generates an HTML file, and opens it in your browser.

### Options

- `-o FILE` - Save HTML to a specific file
- `--no-open` - Don't open browser automatically  
- `--max-bytes N` - Max file size to include (default: 51200)

### Examples

```bash
# Save to custom location
python GitVisuals.py https://github.com/torvalds/linux -o linux.html

# Don't open browser
python GitVisuals.py https://github.com/username/repo --no-open

# Include larger files
python GitVisuals.py https://github.com/username/repo --max-bytes 200000
```

## Features

- Expandable folder tree in sidebar
- File search and filter
- Syntax highlighting with line numbers
- Markdown rendering
- Copy file content button
- Editor and LLM view modes
- Skips binaries and large files

## License

0BSD
