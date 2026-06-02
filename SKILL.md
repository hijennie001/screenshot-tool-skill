---
name: screenshot-tool
description: Windows 截图工具 — 类似微信截图，支持区域选择、调整大小、自动复制剪贴板并保存到桌面。通过 Ctrl+Shift+A 快捷键触发。
allowed-tools: Bash(python:*) Bash(pip:*)
version: 1.0.0
---

# Screenshot Tool (微信风格截图工具)

一个轻量级 Windows 截图工具，类似微信截图功能。

## 触发条件

当用户需要：
- 截取屏幕区域
- 启动截图工具
- 安装/运行截图工具

## 功能特性

- **全局快捷键** Ctrl+Shift+A 触发截图
- **区域选择** 鼠标拖拽选择截图区域
- **调整大小** 8 个方向的调整手柄（四角 + 四边中点）
- **移动选区** 在选区内拖拽可移动位置
- **自动复制** 截图后自动复制到 Windows 剪贴板，可直接粘贴到微信/QQ/钉钉等
- **自动保存** 截图自动保存到桌面，文件名格式 `screenshot_YYYYMMDD_HHMMSS.png`

## 使用方式

### 安装依赖

```bash
pip install Pillow mss keyboard pywin32
```

### 启动工具

```bash
python <skill_dir>/scripts/screenshot_tool.py
```

### 操作说明

| 操作 | 说明 |
|------|------|
| Ctrl+Shift+A | 触发截图 |
| 鼠标拖拽 | 选择截图区域 |
| 拖拽边缘/角落 | 调整选区大小 |
| 拖拽选区内部 | 移动选区 |
| 双击选区 / Enter / ✓按钮 | 确认截图 |
| Esc / 右键 / ✗按钮 | 取消截图 |
| Ctrl+C | 退出程序 |

## 系统要求

- Windows 10/11
- Python 3.8+
- 依赖: Pillow, mss, keyboard, pywin32

## 注意事项

- `keyboard` 库需要管理员权限才能监听全局快捷键
- 截图保存路径默认为用户桌面
- 程序启动后常驻后台，随时按快捷键即可截图
