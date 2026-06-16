# Screenshot & Recording Tool Skill

A WeChat-style screenshot + screen recording tool for Windows, with video trimming support.

## Features

- **Screenshot** (`Ctrl+Shift+A`): Drag to select, resize handles, auto clipboard + save
- **Screen Recording** (`Ctrl+Shift+R`): Region recording with floating timer
- **Video Trimmer**: Trim recorded video with timeline slider before saving

## Requirements

- Windows 10/11
- Python 3.8+

## Installation

### As a standalone tool

```bash
pip install Pillow mss keyboard pywin32 opencv-python numpy
python scripts/screenshot_tool.py
```

### As a Ducc/Claude Code skill

Copy to `~/.claude/skills/screenshot-tool/`

## Usage

1. Run `python scripts/screenshot_tool.py`
2. **Screenshot**: Press `Ctrl+Shift+A` → drag region → Enter/double-click to confirm
3. **Recording**: Press `Ctrl+Shift+R` → select region → recording starts → press again to stop → trim & save

Output files are saved to Desktop:
- Screenshots: `screenshot_YYYYMMDD_HHMMSS.png`
- Recordings: `recording_YYYYMMDD_HHMMSS.avi`

## License

MIT
