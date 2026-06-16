---
name: screenshot-tool
description: Windows 截图录屏工具 — 截图(Ctrl+Shift+A) + 区域录屏(Ctrl+Shift+R)，录制后支持视频时间轴裁剪，自动复制剪贴板并保存到桌面。
allowed-tools: Bash(python:*) Bash(pip:*)
version: 2.0.0
---

# Screenshot & Recording Tool

截图 + 录屏工具，类似微信截图功能，额外支持区域录屏和视频裁剪。

## 触发条件

当用户需要：
- 截取屏幕区域
- 录制屏幕视频
- 裁剪视频片段
- 启动截图/录屏工具

## 功能特性

### 截图 (Ctrl+Shift+A)
- 全局快捷键触发
- 鼠标拖拽选择区域，8方向调整手柄
- 自动复制到剪贴板 + 保存到桌面

### 录屏 (Ctrl+Shift+R)
- 选择录制区域后开始录制
- 右下角浮窗显示录制时长 + 停止按钮
- 再次按快捷键或点击停止结束录制
- 录制完成后弹出裁剪编辑器

### 视频裁剪编辑器
- 预览画面 + 双滑块选择起止时间
- 拖动滑块实时预览对应帧
- 保存裁剪后的视频到桌面

## 使用方式

### 安装依赖

```bash
pip install Pillow mss keyboard pywin32 opencv-python numpy
```

### 启动工具

```bash
python <skill_dir>/scripts/screenshot_tool.py
```

### 操作说明

| 快捷键 | 功能 |
|--------|------|
| Ctrl+Shift+A | 截图 |
| Ctrl+Shift+R | 开始/停止录屏 |
| Ctrl+C | 退出程序 |

## 系统要求

- Windows 10/11
- Python 3.8+
- 依赖: Pillow, mss, keyboard, pywin32, opencv-python, numpy
