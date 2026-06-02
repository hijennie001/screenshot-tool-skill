# Screenshot Tool Skill

A WeChat-style screenshot tool for Windows, packaged as a Claude Code / Ducc skill.

## Features

- **Global Hotkey**: `Ctrl+Shift+A` to trigger screenshot
- **Region Selection**: Drag to select area with visual feedback
- **Resizable**: 8-direction resize handles (corners + edges)
- **Movable**: Drag inside selection to reposition
- **Auto Clipboard**: Copies screenshot to clipboard (paste anywhere)
- **Auto Save**: Saves PNG to Desktop with timestamp

## Requirements

- Windows 10/11
- Python 3.8+

## Installation

### As a standalone tool

```bash
pip install Pillow mss keyboard pywin32
python scripts/screenshot_tool.py
```

### As a Ducc/Claude Code skill

Copy the `screenshot-tool-skill` folder to `~/.claude/skills/screenshot-tool/`

## Usage

1. Run `python scripts/screenshot_tool.py`
2. Press `Ctrl+Shift+A` to start screenshot
3. Drag to select area
4. Adjust with edge/corner handles if needed
5. Double-click / Enter / click ✓ to confirm
6. Press Esc / Right-click / click ✗ to cancel

Screenshots are saved to `~/Desktop/screenshot_YYYYMMDD_HHMMSS.png`

## License

MIT
