"""
Screen Recorder - 区域录屏 + 视频裁剪工具
- 选区录制屏幕
- 录制完成后弹出裁剪编辑器（时间轴裁剪）
- 保存到桌面

Requirements: pip install opencv-python numpy mss keyboard Pillow
"""

import os
import sys
import threading
import time
import tempfile
import tkinter as tk
from tkinter import Canvas, Scale, HORIZONTAL
from datetime import datetime
from PIL import Image, ImageTk
import numpy as np
import cv2
import mss

SAVE_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
FPS = 20
RECORD_HOTKEY = "ctrl+shift+r"


class RegionSelector:
    """全屏遮罩选区（复用截图逻辑的简化版）"""

    def __init__(self):
        self.region = None
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.selecting = False

        self.root = tk.Tk()
        self.root.withdraw()
        self.window = tk.Toplevel(self.root)
        self.window.attributes("-fullscreen", True)
        self.window.attributes("-topmost", True)
        self.window.overrideredirect(True)

        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()

        # 截取全屏作为背景
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])
            self.bg_pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")

        # 半透明遮罩
        mask = Image.new("RGBA", (sw, sh), (0, 0, 0, 100))
        masked = Image.alpha_composite(self.bg_pil.convert("RGBA"), mask)
        self.bg_tk = ImageTk.PhotoImage(masked)

        self.canvas = Canvas(self.window, width=sw, height=sh, highlightthickness=0, cursor="crosshair")
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor="nw", image=self.bg_tk)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_confirm)
        self.window.bind("<Escape>", lambda e: self.cancel())
        self.window.bind("<Return>", lambda e: self.confirm())
        self.window.focus_force()

    def on_press(self, event):
        self.selecting = True
        self.start_x = event.x
        self.start_y = event.y

    def on_drag(self, event):
        if not self.selecting:
            return
        self.end_x = event.x
        self.end_y = event.y
        self.canvas.delete("sel")
        x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
        x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
        # 选区内显示清晰画面
        crop = self.bg_pil.crop((x1, y1, x2, y2))
        self.crop_tk = ImageTk.PhotoImage(crop)
        self.canvas.create_image(x1, y1, anchor="nw", image=self.crop_tk, tags="sel")
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#FF4444", width=2, tags="sel")

    def on_release(self, event):
        self.selecting = False
        self.end_x = event.x
        self.end_y = event.y

    def on_confirm(self, event):
        self.confirm()

    def confirm(self):
        x1 = min(self.start_x, self.end_x)
        y1 = min(self.start_y, self.end_y)
        x2 = max(self.start_x, self.end_x)
        y2 = max(self.start_y, self.end_y)
        if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:
            self.region = (x1, y1, x2, y2)
        self.close()

    def cancel(self):
        self.region = None
        self.close()

    def close(self):
        self.window.destroy()
        self.root.quit()

    def run(self):
        self.root.mainloop()
        try:
            self.root.destroy()
        except Exception:
            pass
        return self.region


class RecordingFloater:
    """录制中的浮窗提示"""

    def __init__(self, on_stop):
        self.on_stop = on_stop
        self.start_time = time.time()
        self.running = True

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        # 放在屏幕右下角
        self.root.geometry("+{}+{}".format(
            self.root.winfo_screenwidth() - 200,
            self.root.winfo_screenheight() - 80
        ))
        self.root.configure(bg="#333333")

        self.label = tk.Label(self.root, text="● 录制中 00:00", fg="#FF4444", bg="#333333",
                              font=("Microsoft YaHei", 11, "bold"))
        self.label.pack(side=tk.LEFT, padx=8, pady=8)

        btn = tk.Button(self.root, text="■ 停止", command=self._stop,
                        bg="#FF4444", fg="white", font=("Microsoft YaHei", 9, "bold"),
                        relief=tk.FLAT, padx=8)
        btn.pack(side=tk.RIGHT, padx=8, pady=8)

        self._update_time()

    def _update_time(self):
        if not self.running:
            return
        elapsed = int(time.time() - self.start_time)
        m, s = divmod(elapsed, 60)
        self.label.config(text=f"● 录制中 {m:02d}:{s:02d}")
        self.root.after(500, self._update_time)

    def _stop(self):
        self.running = False
        self.on_stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class VideoTrimmer:
    """视频裁剪编辑器"""

    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or FPS
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.saved_path = None

        if self.total_frames < 2:
            self.cap.release()
            return

        self.root = tk.Tk()
        self.root.title("视频裁剪")
        self.root.attributes("-topmost", True)

        # 预览尺寸（限制最大 640x480）
        scale = min(640 / self.width, 480 / self.height, 1.0)
        self.preview_w = int(self.width * scale)
        self.preview_h = int(self.height * scale)

        # 预览画布
        self.canvas = Canvas(self.root, width=self.preview_w, height=self.preview_h, bg="black")
        self.canvas.pack(padx=10, pady=10)

        # 起始帧滑块
        tk.Label(self.root, text="起始位置:").pack(anchor="w", padx=10)
        self.start_scale = Scale(self.root, from_=0, to=self.total_frames - 1,
                                 orient=HORIZONTAL, length=self.preview_w,
                                 command=self._on_start_change)
        self.start_scale.pack(padx=10)

        # 结束帧滑块
        tk.Label(self.root, text="结束位置:").pack(anchor="w", padx=10)
        self.end_scale = Scale(self.root, from_=0, to=self.total_frames - 1,
                               orient=HORIZONTAL, length=self.preview_w,
                               command=self._on_end_change)
        self.end_scale.set(self.total_frames - 1)
        self.end_scale.pack(padx=10)

        # 时间标签
        duration = self.total_frames / self.fps
        self.time_label = tk.Label(self.root, text=f"总时长: {duration:.1f}s | 选中: {duration:.1f}s")
        self.time_label.pack(pady=5)

        # 按钮栏
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="保存", command=self._save, bg="#4CAF50", fg="white",
                  font=("Microsoft YaHei", 10), padx=15).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="取消", command=self._cancel, bg="#F44336", fg="white",
                  font=("Microsoft YaHei", 10), padx=15).pack(side=tk.LEFT, padx=10)

        # 显示第一帧
        self._show_frame(0)

    def _on_start_change(self, val):
        frame_idx = int(val)
        if frame_idx >= self.end_scale.get():
            self.start_scale.set(int(self.end_scale.get()) - 1)
            return
        self._show_frame(frame_idx)
        self._update_time_label()

    def _on_end_change(self, val):
        frame_idx = int(val)
        if frame_idx <= self.start_scale.get():
            self.end_scale.set(int(self.start_scale.get()) + 1)
            return
        self._show_frame(frame_idx)
        self._update_time_label()

    def _update_time_label(self):
        start_f = int(self.start_scale.get())
        end_f = int(self.end_scale.get())
        total = self.total_frames / self.fps
        selected = (end_f - start_f) / self.fps
        self.time_label.config(text=f"总时长: {total:.1f}s | 选中: {selected:.1f}s")

    def _show_frame(self, frame_idx):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if not ret:
            return
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb).resize((self.preview_w, self.preview_h))
        self.preview_tk = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.preview_tk)

    def _save(self):
        start_f = int(self.start_scale.get())
        end_f = int(self.end_scale.get())

        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(SAVE_DIR, f"recording_{timestamp}.avi")

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
        for _ in range(end_f - start_f):
            ret, frame = self.cap.read()
            if not ret:
                break
            writer.write(frame)

        writer.release()
        self.saved_path = output_path
        self.cap.release()
        self.root.destroy()
        print(f"[Screen Recorder] Saved: {output_path}")

    def _cancel(self):
        self.cap.release()
        self.root.destroy()

    def run(self):
        if self.total_frames < 2:
            return None
        self.root.mainloop()
        return self.saved_path


class ScreenRecorder:
    """录屏控制器"""

    def __init__(self):
        self.recording = False
        self.record_thread = None
        self.stop_event = threading.Event()
        self.temp_file = None

    def start_recording(self):
        """触发录屏流程"""
        if self.recording:
            self.stop_recording()
            return

        # 选择录制区域
        selector = RegionSelector()
        region = selector.run()
        if not region:
            print("[Screen Recorder] Cancelled")
            return

        x1, y1, x2, y2 = region
        width = x2 - x1
        height = y2 - y1

        # 确保宽高为偶数（编码器要求）
        width = width - (width % 2)
        height = height - (height % 2)

        self.temp_file = os.path.join(tempfile.gettempdir(), "screen_record_temp.avi")
        self.stop_event.clear()
        self.recording = True

        # 启动录制线程
        self.record_thread = threading.Thread(
            target=self._record_loop,
            args=(x1, y1, width, height),
            daemon=True
        )
        self.record_thread.start()

        # 显示录制浮窗
        floater = RecordingFloater(on_stop=self.stop_recording)
        floater.run()

        # 浮窗关闭后等待录制线程结束
        self.record_thread.join(timeout=3)

        # 打开裁剪编辑器
        if os.path.exists(self.temp_file):
            trimmer = VideoTrimmer(self.temp_file)
            trimmer.run()
            # 清理临时文件
            try:
                os.remove(self.temp_file)
            except Exception:
                pass

    def stop_recording(self):
        """停止录制"""
        self.recording = False
        self.stop_event.set()

    def _record_loop(self, x, y, w, h):
        """录制线程"""
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(self.temp_file, fourcc, FPS, (w, h))
        interval = 1.0 / FPS

        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            while not self.stop_event.is_set():
                t0 = time.time()
                img = sct.grab(monitor)
                frame = np.array(img)
                # BGRA -> BGR
                frame = frame[:, :, :3]
                writer.write(frame)
                # 控制帧率
                elapsed = time.time() - t0
                if elapsed < interval:
                    time.sleep(interval - elapsed)

        writer.release()
        print(f"[Screen Recorder] Recording stopped, {self.temp_file}")


# 全局实例
_recorder = ScreenRecorder()


def start_or_stop_recording():
    """快捷键回调"""
    _recorder.start_recording()


if __name__ == "__main__":
    import keyboard as kb
    print(f"[Screen Recorder] Press {RECORD_HOTKEY.upper()} to start/stop recording")
    kb.add_hotkey(RECORD_HOTKEY, start_or_stop_recording)
    try:
        kb.wait()
    except KeyboardInterrupt:
        print("\n[Screen Recorder] Exited")
        sys.exit(0)
