#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YJ-关机助手 v00.33
集成试用 / 注册 / 付费授权系统
"""

import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import subprocess
import threading
import time
import os
import json
import hashlib
import platform

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


# ---------- 授权系统 ----------

class LicenseManager:
    """本地授权管理器"""

    APP_NAME = "YJ-关机助手"
    APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME)

    # 试用/注册/付费 状态
    STATUS_TRIAL_1 = "trial_day1"       # 首日试用
    STATUS_TRIAL_7 = "trial_week"       # 注册后7天试用
    STATUS_EXPIRED = "expired"          # 试用过期
    STATUS_PAID = "paid"                # 永久已付费

    def __init__(self):
        os.makedirs(self.APP_DIR, exist_ok=True)
        self.license_file = os.path.join(self.APP_DIR, "license.json")
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "status": self.STATUS_TRIAL_1,
            "first_install_time": int(time.time()),
            "register_email": "",
            "register_time": 0,
            "license_key": "",
            "machine_id": self._get_machine_id()
        }

    def _save(self):
        try:
            with open(self.license_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    @staticmethod
    def _get_machine_id():
        """生成机器唯一ID"""
        raw = platform.node() + os.environ.get("PROCESSOR_IDENTIFIER", "") + os.environ.get("COMPUTERNAME", "")
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def generate_license_key(machine_id):
        """根据机器码生成激活码（伪算法）"""
        raw = f"YJ-{machine_id}-2026-FOREVER"
        return hashlib.sha256(raw.encode()).hexdigest().upper()[:24]

    def get_status(self):
        """获取当前授权状态"""
        now = int(time.time())
        elapsed_days = (now - self.data["first_install_time"]) // 86400

        # 已付费 -> 永久可用
        if self.data["status"] == self.STATUS_PAID:
            return self.STATUS_PAID

        # 注册试用7天
        if self.data["status"] == self.STATUS_TRIAL_7:
            if self.data["register_time"] > 0:
                elapsed_reg = (now - self.data["register_time"]) // 86400
                if elapsed_reg < 7:
                    return self.STATUS_TRIAL_7
                else:
                    self.data["status"] = self.STATUS_EXPIRED
                    self._save()
                    return self.STATUS_EXPIRED

        # 首日试用
        if elapsed_days < 1:
            return self.STATUS_TRIAL_1
        else:
            self.data["status"] = self.STATUS_EXPIRED
            self._save()
            return self.STATUS_EXPIRED

    def register(self, email):
        """注册（输入邮箱激活7天试用）"""
        self.data["status"] = self.STATUS_TRIAL_7
        self.data["register_email"] = email
        self.data["register_time"] = int(time.time())
        self._save()

    def activate(self, license_key):
        """用激活码永久解锁"""
        expected = self.generate_license_key(self.data["machine_id"])
        if license_key.strip().upper() == expected:
            self.data["status"] = self.STATUS_PAID
            self.data["license_key"] = license_key.strip()
            self._save()
            return True
        return False

    def get_machine_id_display(self):
        return self.data["machine_id"]


# ---------- 主程序 ----------

class ShutdownAssistant:
    def __init__(self, root):
        self.root = root
        self.license_mgr = LicenseManager()
        self.authorized = False  # 当前会话是否已解锁
        self.remaining_seconds = 0
        self.is_counting = False
        self.cancel_flag = threading.Event()
        self.active_btn = None

        self.C_BG = "#f0f2f5"
        self.C_CARD = "#f0f0f0"
        self.C_WHITE = "#ffffff"
        self.C_BORDER = "#d0d5dd"
        self.C_BLUE_LIGHT = "#a0c4ff"
        self.C_BLUE_DARK = "#1a56db"
        self.C_BLUE = "#1a56db"
        self.C_RED = "#d93025"
        self.C_GRAY_DARK = "#1f2937"
        self.C_GRAY_MED = "#4b5563"
        self.C_GRAY_LIGHT = "#9ca3af"
        self.C_DISABLED_BG = "#e5e7eb"
        self.C_DISABLED_FG = "#9ca3af"

        self.FONT_TITLE = ("微软雅黑", 14, "bold")
        self.FONT_SUBTITLE = ("微软雅黑", 9)
        self.FONT_SECTION = ("微软雅黑", 11, "bold")
        self.FONT_BODY = ("微软雅黑", 10)
        self.FONT_BTN = ("微软雅黑", 10, "bold")
        self.FONT_COUNTDOWN = ("微软雅黑", 26, "bold")
        self.FONT_FOOTER = ("微软雅黑", 9)

        self.root.title("YJ-关机助手")
        self.root.geometry("420x580")
        self.root.resizable(False, False)
        self.root.configure(bg=self.C_BG)

        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._build_ui()
        # 启动时检查授权
        self.root.after(200, self._check_license)

    def _build_ui(self):
        main = tk.Frame(self.root, bg=self.C_BG)
        main.pack(fill="both", expand=True, padx=20, pady=12)

        # 区域1：软件名称
        tk.Label(main, text="YJ-关机助手", font=self.FONT_TITLE,
                 bg=self.C_BG, fg=self.C_BLUE).pack(anchor="w")
        tk.Label(main, text="简单好用的 Windows 定时关机小工具  v00.33",
                 font=self.FONT_SUBTITLE, bg=self.C_BG,
                 fg=self.C_GRAY_MED, anchor="w").pack(fill="x", pady=(0, 10))

        # 区域2：快速关机
        quick_card = tk.Frame(main, bg=self.C_CARD,
                              highlightbackground=self.C_BORDER,
                              highlightthickness=1, bd=0)
        quick_card.pack(fill="x", pady=(0, 8))
        tk.Label(quick_card, text="快速关机", font=self.FONT_SECTION,
                 bg=self.C_CARD, fg=self.C_BLUE).pack(fill="x", padx=12, pady=6, anchor="w")

        btn_row = tk.Frame(quick_card, bg=self.C_CARD)
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        self.quick_btns = []
        for text, sec, label in [
            ("3 分钟", 180, "3分钟"),
            ("10 分钟", 600, "10分钟"),
            ("30 分钟", 1800, "30分钟"),
            ("60 分钟", 3600, "60分钟"),
        ]:
            btn = tk.Button(
                btn_row, text=text,
                font=self.FONT_BTN,
                bg=self.C_BLUE_LIGHT, fg="#ffffff",
                activebackground=self.C_BLUE_DARK, activeforeground="white",
                relief="flat", bd=0, cursor="hand2",
                command=lambda s=sec, l=label: self._quick_click(s, l)
            )
            btn.pack(side="left", fill="x", expand=True, padx=3, ipady=4)
            self.quick_btns.append(btn)

        # 区域3：定时关机
        timed_card = tk.Frame(main, bg=self.C_CARD,
                              highlightbackground=self.C_BORDER,
                              highlightthickness=1, bd=0)
        timed_card.pack(fill="x", pady=(0, 8))
        tk.Label(timed_card, text="定时关机", font=self.FONT_SECTION,
                 bg=self.C_CARD, fg=self.C_BLUE).pack(fill="x", padx=12, pady=6, anchor="w")

        date_row = tk.Frame(timed_card, bg=self.C_CARD)
        date_row.pack(fill="x", padx=12, pady=(0, 4))
        tk.Label(date_row, text="日期", font=self.FONT_BODY,
                 bg=self.C_CARD, fg=self.C_GRAY_MED, width=4, anchor="w").pack(side="left")
        self.date_combo = ttk.Combobox(date_row, width=28, state="readonly", font=self.FONT_BODY)
        self.date_combo.pack(side="left", fill="x", expand=True)
        self._populate_dates()
        self.date_combo.bind("<<ComboboxSelected>>", self._on_date_changed)

        time_row = tk.Frame(timed_card, bg=self.C_CARD)
        time_row.pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(time_row, text="时间", font=self.FONT_BODY,
                 bg=self.C_CARD, fg=self.C_GRAY_MED, width=4, anchor="w").pack(side="left")
        self.time_combo = ttk.Combobox(time_row, width=28, state="readonly", font=self.FONT_BODY)
        self.time_combo.pack(side="left", fill="x", expand=True)
        self._populate_times()

        self.btn_timed = tk.Button(
            timed_card, text="设置定时关机",
            font=self.FONT_BTN,
            bg=self.C_BLUE_LIGHT, fg="#ffffff",
            activebackground=self.C_BLUE_DARK, activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
            command=self.start_timed
        )
        self.btn_timed.pack(fill="x", padx=12, pady=(0, 10), ipady=4)

        # 倒计时 & 取消
        cd_frame = tk.Frame(main, bg=self.C_BG)
        cd_frame.pack(fill="x", pady=(2, 0))

        self.countdown_label = tk.Label(
            cd_frame, text="", font=self.FONT_COUNTDOWN,
            bg=self.C_BG, fg=self.C_BLUE
        )
        self.countdown_label.pack(pady=4)

        self.status_label = tk.Label(
            cd_frame, text="", font=self.FONT_SUBTITLE,
            bg=self.C_BG, fg=self.C_GRAY_MED
        )
        self.status_label.pack(pady=2)

        self.btn_cancel = tk.Button(
            cd_frame, text="取消关机",
            font=self.FONT_BTN,
            bg=self.C_DISABLED_BG, fg=self.C_DISABLED_FG,
            activebackground="#d1d5db", activeforeground=self.C_GRAY_MED,
            relief="flat", bd=0, cursor="hand2",
            state="disabled",
            command=self.cancel_shutdown
        )
        self.btn_cancel.pack(pady=6, ipadx=20, ipady=3)

        # 联系方式
        tk.Label(main, text="GitHub: caesaryin2026  微信: kslovemaggie",
                 font=self.FONT_FOOTER, bg=self.C_BG,
                 fg=self.C_GRAY_DARK, anchor="center").pack(pady=(10, 0))

    # ---------- 授权检测 ----------

    def _check_license(self):
        status = self.license_mgr.get_status()
        if status == LicenseManager.STATUS_PAID:
            self.authorized = True
            self.status_label.config(text="已激活永久许可")
            return

        if status == LicenseManager.STATUS_TRIAL_1:
            remain = 86400 - (int(time.time()) - self.license_mgr.data["first_install_time"])
            hours = remain // 3600
            mins = (remain % 3600) // 60
            self.authorized = True
            self._show_license_notice(f"试用剩余 {hours}小时{mins}分", show_tip=True)
            return

        if status == LicenseManager.STATUS_TRIAL_7:
            remain = 7 * 86400 - (int(time.time()) - self.license_mgr.data["register_time"])
            days = remain // 86400
            hours = (remain % 86400) // 3600
            self.authorized = True
            self._show_license_notice(f"注册试用剩余 {days}天{hours}小时", show_tip=True)
            return

        # 已过期：功能降级
        self.authorized = False
        self._show_expired_dialog()

    def _show_license_notice(self, msg, show_tip=False):
        self.status_label.config(text=msg, fg=self.C_GRAY_MED)
        if show_tip:
            # 在底部加一个小字提示
            pass

    def _show_expired_dialog(self):
        """试用过期 → 显示付费弹窗"""
        top = tk.Toplevel(self.root)
        top.title("授权已过期")
        top.geometry("380x320")
        top.resizable(False, False)
        top.configure(bg="#ffffff")
        top.transient(self.root)
        top.grab_set()

        # 居中
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 380) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 320) // 2
        top.geometry(f"+{x}+{y}")

        tk.Label(top, text="YJ-关机助手", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#1a56db").pack(pady=(20, 5))

        tk.Label(top, text="试用已过期", font=("微软雅黑", 11),
                 bg="#ffffff", fg="#d93025").pack(pady=(0, 10))

        info_frame = tk.Frame(top, bg="#f8f9fa",
                              highlightbackground="#e0e0e0",
                              highlightthickness=1, bd=0)
        info_frame.pack(fill="x", padx=30, pady=5, ipady=8)

        tk.Label(info_frame, text="功能被限制：", font=("微软雅黑", 9, "bold"),
                 bg="#f8f9fa", fg="#4b5563", anchor="w").pack(padx=12, pady=(8, 2), fill="x")
        tk.Label(info_frame, text="• 快速关机：仅可用 3分钟\n• 定时关机：不可用",
                 font=("微软雅黑", 9),
                 bg="#f8f9fa", fg="#6b7280", anchor="w", justify="left").pack(padx=12, fill="x")

        tk.Label(info_frame, text="机器码：" + self.license_mgr.get_machine_id_display(),
                 font=("微软雅黑", 8), bg="#f8f9fa",
                 fg="#9ca3af", anchor="w").pack(padx=12, pady=(8, 4), fill="x")

        btn_frame = tk.Frame(top, bg="#ffffff")
        btn_frame.pack(pady=(10, 0))

        tk.Button(btn_frame, text="💰 付费激活（¥9.9永久）",
                  font=("微软雅黑", 10, "bold"),
                  bg="#1a56db", fg="white",
                  activebackground="#1648c0", activeforeground="white",
                  relief="flat", bd=0, cursor="hand2",
                  command=lambda: self._show_activate_dialog(top)
                  ).pack(pady=3, ipady=3, fill="x", padx=40)

        tk.Button(btn_frame, text="输入激活码",
                  font=("微软雅黑", 9),
                  bg="#e5e7eb", fg="#4b5563",
                  activebackground="#d1d5db", activeforeground="#1f2937",
                  relief="flat", bd=0, cursor="hand2",
                  command=lambda: self._show_activate_code_dialog(top)
                  ).pack(pady=3, ipady=3, fill="x", padx=40)

        # 关闭时也不退出程序
        top.protocol("WM_DELETE_WINDOW", lambda: self._on_expired_close(top))

    def _on_expired_close(self, top):
        top.destroy()
        # 降级提示
        self.status_label.config(text="试用已过期 - 功能降级模式", fg=self.C_RED)

    def _show_register_dialog(self, parent):
        """注册（邮箱换7天试用）"""
        email = simpledialog.askstring("注册试用",
                                        "输入您的邮箱，获取7天试用：",
                                        parent=parent)
        if email and "@" in email:
            self.license_mgr.register(email)
            messagebox.showinfo("注册成功", f"已为 {email} 激活7天试用！", parent=parent)
            parent.destroy()
            self._check_license()
        elif email:
            messagebox.showerror("格式错误", "请输入有效的邮箱地址！", parent=parent)

    def _show_activate_dialog(self, parent):
        """付费激活弹窗"""
        top = tk.Toplevel(parent)
        top.title("付费激活")
        top.geometry("360x280")
        top.resizable(False, False)
        top.configure(bg="#ffffff")
        top.transient(parent)
        top.grab_set()

        tk.Label(top, text="💳 付费激活", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#1a56db").pack(pady=(20, 10))

        tk.Label(top, text="¥9.9 永久使用", font=("微软雅黑", 11),
                 bg="#ffffff", fg="#d93025").pack(pady=(0, 15))

        tk.Label(top, text="机器码：" + self.license_mgr.get_machine_id_display(),
                 font=("微软雅黑", 9), bg="#ffffff",
                 fg="#9ca3af").pack()

        tk.Label(top, text="请将机器码发给开发者，微信：kslovemaggie",
                 font=("微软雅黑", 9), bg="#ffffff",
                 fg="#4b5563").pack(pady=(15, 5))

        tk.Label(top, text="付款后开发者会返回激活码",
                 font=("微软雅汉", 9), bg="#ffffff",
                 fg="#4b5563").pack(pady=(0, 10))

        tk.Button(top, text="输入激活码",
                  font=("微软雅黑", 10, "bold"),
                  bg="#1a56db", fg="white",
                  activebackground="#1648c0", activeforeground="white",
                  relief="flat", bd=0, cursor="hand2",
                  command=lambda: [top.destroy(), self._show_activate_code_dialog(parent)]
                  ).pack(pady=5, ipady=3, fill="x", padx=40)

    def _show_activate_code_dialog(self, parent):
        """输入激活码"""
        code = simpledialog.askstring("激活",
                                       "请输入激活码：",
                                       parent=parent)
        if code:
            if self.license_mgr.activate(code):
                messagebox.showinfo("激活成功", "🎉 永久许可已激活！感谢支持！", parent=parent)
                if parent and parent.winfo_exists():
                    parent.destroy()
                self._check_license()
            else:
                messagebox.showerror("激活失败", "激活码无效，请检查后重试。", parent=parent)

    # ---------- 功能 ----------

    def _verify_authorized(self, action_name="此功能"):
        """检查授权，未授权则降级提示"""
        if self.authorized:
            return True
        # 降级模式：只允许3分钟
        return False

    def _quick_click(self, seconds, label):
        status = self.license_mgr.get_status()
        if status == LicenseManager.STATUS_EXPIRED:
            if seconds > 180:
                messagebox.showinfo("功能受限",
                                    "试用已过期，快速关机仅支持3分钟。\n请付费解锁全部功能。")
                return
            # 3分钟还能用
        elif not self.authorized:
            if seconds > 180:
                messagebox.showinfo("功能受限", "请激活后使用全部功能。")
                return

        for b in self.quick_btns:
            b.config(bg=self.C_BLUE_LIGHT, fg="#ffffff")
        btn_map = {180: self.quick_btns[0], 600: self.quick_btns[1],
                   1800: self.quick_btns[2], 3600: self.quick_btns[3]}
        btn = btn_map.get(seconds)
        if btn:
            btn.config(bg=self.C_BLUE_DARK, fg="white")
            self.active_btn = btn

        if not messagebox.askyesno("确认关机",
                                    f"系统将在 {label} 后自动关机。\n"
                                    "请保存好当前工作！\n\n是否继续？"):
            if btn:
                btn.config(bg=self.C_BLUE_LIGHT, fg="#ffffff")
                self.active_btn = None
            return
        self._start_countdown(seconds, label)

    def start_timed(self):
        # 过期用户不可用定时关机
        status = self.license_mgr.get_status()
        if status == LicenseManager.STATUS_EXPIRED:
            self._show_expired_dialog()
            return
        if not self.authorized:
            self._show_expired_dialog()
            return

        try:
            y, mo, d = self.selected_date.split("-")
            h, mi = self.time_combo.get().split(":")
            y, mo, d, h, mi = int(y), int(mo), int(d), int(h), int(mi)
            target_ts = time.mktime((y, mo, d, h, mi, 0, 0, 0, -1))
            diff = int(target_ts - time.time())
            if diff <= 0:
                messagebox.showerror("时间错误", "指定的日期时间已过！\n请选择未来的时间。")
                return
            target_str = f"{y}年{mo}月{d}日 {h:02d}:{mi:02d}"
            days = diff // 86400
            hours = (diff % 86400) // 3600
            mins = (diff % 3600) // 60
            parts = []
            if days > 0: parts.append(f"{days}天")
            if hours > 0: parts.append(f"{hours}小时")
            if mins > 0: parts.append(f"{mins}分")
            desc = "".join(parts) if parts else "不到1分钟"
            if not messagebox.askyesno("确认关机",
                                       f"将在 {target_str} 自动关机。\n"
                                       f"距离现在约 {desc}。\n\n是否继续？"):
                return
            self._start_countdown(diff, target_str)
        except Exception:
            messagebox.showerror("输入错误", "请选择有效的日期和时间！")

    def _start_countdown(self, total_seconds, label):
        self.remaining_seconds = total_seconds
        self.cancel_flag.clear()
        self.is_counting = True
        for b in self.quick_btns:
            b.config(state="disabled")
        self.btn_timed.config(state="disabled")
        self.date_combo.config(state="disabled")
        self.time_combo.config(state="disabled")

        self.btn_cancel.config(state="normal", bg=self.C_RED,
                               fg="white", activebackground="#b3261e")
        self.status_label.config(text=f"已设置关机 ({label})", fg=self.C_GRAY_MED)
        self._execute_shutdown(total_seconds)
        self._update_countdown_display()

    def _execute_shutdown(self, total_seconds):
        def run():
            try:
                subprocess.run(["shutdown", "/a"], capture_output=True, timeout=5)
                subprocess.run(
                    ["shutdown", "/s", "/t", str(total_seconds),
                     "/c", "YJ-关机助手：定时关机"],
                    capture_output=True, timeout=5
                )
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "执行错误", f"无法执行关机命令：{str(e)}"))
        threading.Thread(target=run, daemon=True).start()

    def _update_countdown_display(self):
        if not self.is_counting:
            return
        if self.remaining_seconds <= 0:
            self.countdown_label.config(text="正在关机...")
            return
        self.remaining_seconds -= 1
        h = self.remaining_seconds // 3600
        m = (self.remaining_seconds % 3600) // 60
        s = self.remaining_seconds % 60
        display = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        if self.remaining_seconds < 30:
            color = self.C_RED
        elif self.remaining_seconds < 120:
            color = self.C_GRAY_MED
        else:
            color = self.C_BLUE
        self.countdown_label.config(text=display, fg=color)
        self.root.after(1000, self._update_countdown_display)

    def cancel_shutdown(self):
        if not messagebox.askyesno("取消关机", "确定要取消已设置的关机吗？"):
            return
        self.is_counting = False
        self.cancel_flag.set()
        self.remaining_seconds = 0
        try:
            subprocess.run(["shutdown", "/a"], capture_output=True, timeout=5)
        except Exception:
            pass
        self.countdown_label.config(text="")
        self.status_label.config(text="已取消关机")
        self.btn_cancel.config(state="disabled", bg=self.C_DISABLED_BG, fg=self.C_DISABLED_FG)
        for b in self.quick_btns:
            b.config(state="normal", bg=self.C_BLUE_LIGHT, fg="#ffffff")
        self.btn_timed.config(state="normal", bg=self.C_BLUE_LIGHT, fg="#ffffff")
        self.date_combo.config(state="readonly")
        self.time_combo.config(state="readonly")
        self.active_btn = None
        self.root.after(2000, lambda: self.status_label.config(text=""))

    # ---------- 日期时间 ----------

    def _populate_dates(self):
        now = time.localtime()
        dates = []
        for i in range(31):
            if i < 30:
                t = time.mktime((now.tm_year, now.tm_mon, now.tm_mday + i,
                                 0, 0, 0, 0, 0, -1))
                lt = time.localtime(t)
                label = f"{lt.tm_year}年{lt.tm_mon:02d}月{lt.tm_mday:02d}日"
                if i == 0: label += " (今天)"
                elif i == 1: label += " (明天)"
                value = f"{lt.tm_year}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"
            else:
                t = time.mktime((now.tm_year + 1, now.tm_mon, now.tm_mday,
                                 0, 0, 0, 0, 0, -1))
                lt = time.localtime(t)
                label = f"{lt.tm_year}年{lt.tm_mon:02d}月{lt.tm_mday:02d}日 (1年後)"
                value = f"{lt.tm_year}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"
            dates.append((label, value))
        self.date_options = dates
        self.date_combo["values"] = [d[0] for d in dates]
        self.date_combo.current(0)
        self.selected_date = dates[0][1]

    def _on_date_changed(self, event):
        idx = self.date_combo.current()
        if 0 <= idx < len(self.date_options):
            self.selected_date = self.date_options[idx][1]

    def _populate_times(self):
        times = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
        self.time_combo["values"] = times
        self.time_combo.set("22:00")


def main():
    root = tk.Tk()
    app = ShutdownAssistant(root)
    root.mainloop()


if __name__ == "__main__":
    main()
