"""
Screenshot & Screen Recorder Tool
- Ctrl+Shift+A 截图
- Ctrl+Shift+R 录屏（带视频裁剪）

Requirements: pip install Pillow mss keyboard pywin32 opencv-python numpy
Platform: Windows 10/11
"""

import os
import io
import sys
import tkinter as tk
from tkinter import Canvas
from datetime import datetime
from PIL import Image, ImageTk
import mss
import keyboard
import win32clipboard

# ============== 配置 ==============
HOTKEY = "ctrl+shift+a"
SAVE_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
MASK_COLOR = (0, 0, 0, 100)  # 遮罩颜色 RGBA
BORDER_COLOR = "#00AAFF"
HANDLE_SIZE = 6


def copy_image_to_clipboard(image: Image.Image):
    """将 PIL Image 复制到 Windows 剪贴板（BMP 格式）"""
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]  # 去掉 BMP 文件头（14字节）
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()


def save_image_to_desktop(image: Image.Image):
    """保存截图到桌面"""
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(SAVE_DIR, filename)
    image.save(filepath, "PNG")
    print(f"[Screenshot Tool] Saved: {filepath}")
    return filepath


class ScreenshotOverlay:
    """全屏覆盖窗口，用于选择截图区域"""

    def __init__(self, screenshot: Image.Image):
        self.screenshot = screenshot
        self.result = None

        # 选区坐标
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.selecting = False
        self.selected = False

        # 调整大小相关
        self.resizing = False
        self.resize_handle = None
        self.moving = False
        self.move_start_x = 0
        self.move_start_y = 0

        # 创建窗口
        self.root = tk.Tk()
        self.root.withdraw()

        self.window = tk.Toplevel(self.root)
        self.window.attributes("-fullscreen", True)
        self.window.attributes("-topmost", True)
        self.window.overrideredirect(True)

        # 获取屏幕尺寸
        self.screen_width = self.window.winfo_screenwidth()
        self.screen_height = self.window.winfo_screenheight()

        # 创建 Canvas
        self.canvas = Canvas(
            self.window,
            width=self.screen_width,
            height=self.screen_height,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack()

        # 准备图片
        self.bg_image = ImageTk.PhotoImage(self.screenshot)

        # 创建带遮罩的背景
        self.mask_image = Image.new("RGBA", (self.screen_width, self.screen_height), MASK_COLOR)
        self.masked_bg = Image.alpha_composite(
            self.screenshot.convert("RGBA"), self.mask_image
        )
        self.masked_bg_tk = ImageTk.PhotoImage(self.masked_bg)

        # 显示遮罩背景
        self.canvas.create_image(0, 0, anchor="nw", image=self.masked_bg_tk, tags="bg")

        # 绑定事件
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.window.bind("<Escape>", self.on_escape)
        self.window.bind("<Return>", self.on_confirm)

        self.window.focus_force()

    def get_selection_rect(self):
        """获取规范化的选区坐标"""
        x1 = min(self.start_x, self.end_x)
        y1 = min(self.start_y, self.end_y)
        x2 = max(self.start_x, self.end_x)
        y2 = max(self.start_y, self.end_y)
        return x1, y1, x2, y2

    def get_handle_at(self, x, y):
        """检测鼠标是否在调整手柄上"""
        if not self.selected:
            return None
        x1, y1, x2, y2 = self.get_selection_rect()
        hs = HANDLE_SIZE + 3

        handles = {
            "tl": (x1, y1),
            "t": ((x1 + x2) // 2, y1),
            "tr": (x2, y1),
            "l": (x1, (y1 + y2) // 2),
            "r": (x2, (y1 + y2) // 2),
            "bl": (x1, y2),
            "b": ((x1 + x2) // 2, y2),
            "br": (x2, y2),
        }

        for handle_name, (hx, hy) in handles.items():
            if abs(x - hx) <= hs and abs(y - hy) <= hs:
                return handle_name
        return None

    def is_inside_selection(self, x, y):
        """检测是否在选区内部"""
        if not self.selected:
            return False
        x1, y1, x2, y2 = self.get_selection_rect()
        return x1 < x < x2 and y1 < y < y2

    def on_motion(self, event):
        """鼠标移动时更新光标样式"""
        if self.selecting or self.resizing or self.moving:
            return

        handle = self.get_handle_at(event.x, event.y)
        if handle:
            cursors = {
                "tl": "top_left_corner",
                "tr": "top_right_corner",
                "bl": "bottom_left_corner",
                "br": "bottom_right_corner",
                "t": "sb_v_double_arrow",
                "b": "sb_v_double_arrow",
                "l": "sb_h_double_arrow",
                "r": "sb_h_double_arrow",
            }
            self.canvas.config(cursor=cursors.get(handle, "crosshair"))
        elif self.is_inside_selection(event.x, event.y):
            self.canvas.config(cursor="fleur")
        else:
            self.canvas.config(cursor="crosshair")

    def on_press(self, event):
        """鼠标按下"""
        if self.selected and self._check_toolbar_click(event.x, event.y):
            return

        handle = self.get_handle_at(event.x, event.y)
        if handle:
            self.resizing = True
            self.resize_handle = handle
            return

        if self.is_inside_selection(event.x, event.y):
            self.moving = True
            self.move_start_x = event.x
            self.move_start_y = event.y
            return

        self.selecting = True
        self.selected = False
        self.start_x = event.x
        self.start_y = event.y
        self.end_x = event.x
        self.end_y = event.y

    def on_drag(self, event):
        """鼠标拖拽"""
        if self.selecting:
            self.end_x = event.x
            self.end_y = event.y
            self.draw_selection()
        elif self.resizing:
            self._do_resize(event.x, event.y)
            self.draw_selection()
        elif self.moving:
            dx = event.x - self.move_start_x
            dy = event.y - self.move_start_y
            self.start_x += dx
            self.start_y += dy
            self.end_x += dx
            self.end_y += dy
            self.move_start_x = event.x
            self.move_start_y = event.y
            self.draw_selection()

    def on_release(self, event):
        """鼠标释放"""
        if self.selecting:
            self.selecting = False
            self.end_x = event.x
            self.end_y = event.y
            x1, y1, x2, y2 = self.get_selection_rect()
            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                self.selected = True
                self.draw_selection()
        elif self.resizing:
            self.resizing = False
        elif self.moving:
            self.moving = False

    def _do_resize(self, x, y):
        """根据手柄方向调整选区"""
        handle = self.resize_handle
        if self.start_x > self.end_x:
            self.start_x, self.end_x = self.end_x, self.start_x
        if self.start_y > self.end_y:
            self.start_y, self.end_y = self.end_y, self.start_y

        if "l" in handle:
            self.start_x = x
        if "r" in handle:
            self.end_x = x
        if "t" in handle:
            self.start_y = y
        if "b" in handle:
            self.end_y = y

    def draw_selection(self):
        """绘制选区"""
        self.canvas.delete("selection")
        self.canvas.delete("handles")
        self.canvas.delete("toolbar")
        self.canvas.delete("clear_area")
        self.canvas.delete("size_label")

        x1, y1, x2, y2 = self.get_selection_rect()
        if abs(x2 - x1) < 2 or abs(y2 - y1) < 2:
            return

        # 选区内显示原始截图（无遮罩）
        crop_region = self.screenshot.crop((x1, y1, x2, y2))
        self.clear_area_tk = ImageTk.PhotoImage(crop_region)
        self.canvas.create_image(x1, y1, anchor="nw", image=self.clear_area_tk, tags="clear_area")

        # 边框
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=BORDER_COLOR, width=2, tags="selection"
        )

        # 尺寸标签
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        size_text = f"{width} \u00d7 {height}"
        label_y = y1 - 25 if y1 > 30 else y2 + 5
        self.canvas.create_rectangle(
            x1, label_y, x1 + len(size_text) * 8 + 10, label_y + 20,
            fill="#333333", outline="", tags="size_label"
        )
        self.canvas.create_text(
            x1 + 5, label_y + 10,
            text=size_text, fill="white", anchor="w",
            font=("Microsoft YaHei", 9), tags="size_label"
        )

        # 调整手柄
        if self.selected:
            handles_pos = [
                (x1, y1), ((x1 + x2) // 2, y1), (x2, y1),
                (x1, (y1 + y2) // 2), (x2, (y1 + y2) // 2),
                (x1, y2), ((x1 + x2) // 2, y2), (x2, y2),
            ]
            for hx, hy in handles_pos:
                self.canvas.create_rectangle(
                    hx - HANDLE_SIZE, hy - HANDLE_SIZE,
                    hx + HANDLE_SIZE, hy + HANDLE_SIZE,
                    fill=BORDER_COLOR, outline="white", width=1, tags="handles"
                )
            self._draw_toolbar(x2, y2)

    def _draw_toolbar(self, x2, y2):
        """绘制确认/取消工具栏"""
        toolbar_y = y2 + 8
        toolbar_x = x2 - 70

        if toolbar_y + 35 > self.screen_height:
            toolbar_y = y2 - 40
        if toolbar_x < 0:
            toolbar_x = 0

        self.canvas.create_rectangle(
            toolbar_x, toolbar_y,
            toolbar_x + 70, toolbar_y + 32,
            fill="#FFFFFF", outline="#CCCCCC", tags="toolbar"
        )

        # 确认按钮
        self.canvas.create_rectangle(
            toolbar_x + 2, toolbar_y + 2,
            toolbar_x + 34, toolbar_y + 30,
            fill="#4CAF50", outline="", tags="toolbar"
        )
        self.canvas.create_text(
            toolbar_x + 18, toolbar_y + 16,
            text="\u2713", fill="white", font=("Arial", 14, "bold"), tags="toolbar"
        )

        # 取消按钮
        self.canvas.create_rectangle(
            toolbar_x + 36, toolbar_y + 2,
            toolbar_x + 68, toolbar_y + 30,
            fill="#F44336", outline="", tags="toolbar"
        )
        self.canvas.create_text(
            toolbar_x + 52, toolbar_y + 16,
            text="\u2717", fill="white", font=("Arial", 14, "bold"), tags="toolbar"
        )

        self._toolbar_confirm = (toolbar_x + 2, toolbar_y + 2, toolbar_x + 34, toolbar_y + 30)
        self._toolbar_cancel = (toolbar_x + 36, toolbar_y + 2, toolbar_x + 68, toolbar_y + 30)

    def _check_toolbar_click(self, x, y):
        """检查是否点击了工具栏按钮"""
        if hasattr(self, "_toolbar_confirm"):
            bx1, by1, bx2, by2 = self._toolbar_confirm
            if bx1 <= x <= bx2 and by1 <= y <= by2:
                self.confirm_screenshot()
                return True

        if hasattr(self, "_toolbar_cancel"):
            bx1, by1, bx2, by2 = self._toolbar_cancel
            if bx1 <= x <= bx2 and by1 <= y <= by2:
                self.cancel()
                return True
        return False

    def on_double_click(self, event):
        """双击确认截图"""
        if self.selected and self.is_inside_selection(event.x, event.y):
            self.confirm_screenshot()

    def on_right_click(self, event):
        """右键取消"""
        self.cancel()

    def on_escape(self, event):
        """Esc 取消"""
        self.cancel()

    def on_confirm(self, event):
        """Enter 确认"""
        if self.selected:
            self.confirm_screenshot()

    def confirm_screenshot(self):
        """确认并裁剪截图"""
        x1, y1, x2, y2 = self.get_selection_rect()
        self.result = self.screenshot.crop((x1, y1, x2, y2))
        self.close()

    def cancel(self):
        """取消截图"""
        self.result = None
        self.close()

    def close(self):
        """关闭窗口"""
        self.window.destroy()
        self.root.quit()

    def run(self):
        """运行截图选择界面"""
        self.root.mainloop()
        try:
            self.root.destroy()
        except Exception:
            pass
        return self.result


def take_screenshot():
    """执行截图流程"""
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        sct_img = sct.grab(monitor)
        screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    overlay = ScreenshotOverlay(screenshot)
    result = overlay.run()

    if result:
        copy_image_to_clipboard(result)
        filepath = save_image_to_desktop(result)
        print(f"[Screenshot Tool] Copied to clipboard & saved: {filepath}")
    else:
        print("[Screenshot Tool] Cancelled")


def main():
    """主函数：注册全局快捷键并等待"""
    # 导入录屏模块
    from screen_recorder import start_or_stop_recording, RECORD_HOTKEY

    print("=" * 50)
    print("  Screenshot & Recording Tool")
    print("=" * 50)
    print(f"  Screenshot: {HOTKEY.upper()}")
    print(f"  Recording:  {RECORD_HOTKEY.upper()}")
    print(f"  Save to: {SAVE_DIR}")
    print("  Usage:")
    print("    [Screenshot]")
    print("    - Drag to select area")
    print("    - Drag edges/corners to resize")
    print("    - Double-click / Enter to confirm")
    print("    - Esc / Right-click to cancel")
    print("    [Recording]")
    print("    - Select region, then recording starts")
    print("    - Press hotkey again or click Stop")
    print("    - Trim video with slider, then save")
    print("  Press Ctrl+C to exit")
    print("=" * 50)

    keyboard.add_hotkey(HOTKEY, take_screenshot)
    keyboard.add_hotkey(RECORD_HOTKEY, start_or_stop_recording)

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[Tool] Exited")
        sys.exit(0)


if __name__ == "__main__":
    main()
