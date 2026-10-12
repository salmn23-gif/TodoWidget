# -*- coding: utf-8 -*-
"""
ودجت قائمة المهام - سطح مكتب ويندوز 11
- اكتب المهمة ثم Enter (أو زر +)
- انقر على المهمة لإنجازها، ومرّر الفأرة فوقها لتظهر علامة الحذف
- اسحب الودجت من أي مكان فارغ لتحريكه (يُحفظ مكانه)
- كليك يمين: تثبيت فوق النوافذ / حذف المكتملة / إغلاق
- بدون أي مكتبات خارجية
"""
import ctypes
import json
import os
import tkinter as tk
from tkinter import font as tkfont

# ---------- وضوح الخطوط على الشاشات عالية الدقة ----------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ---------- الألوان ----------
KEY = "#010203"       # لون الشفافية (لا يظهر)
CARD = "#15171E"
BORDER = "#262A35"
FIELD = "#1E212B"
HOVER = "#1B1E27"
LINE = "#1F222C"
TEXT = "#F1F3F7"
MUTED = "#808897"
RING = "#4A5163"
ACCENT = "#6C8CFF"

FAMILY = "Segoe UI"
W, H, R = 330, 480, 26
PLACEHOLDER = "أضف مهمة جديدة…"
AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
CONFIG = os.path.join(os.path.expanduser("~"), ".todo_widget.json")


def ar(n):
    return str(n).translate(AR)


def load_data():
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_data(data):
    try:
        tmp = CONFIG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, CONFIG)
    except Exception:
        pass


def rounded_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class TodoWidget:
    def __init__(self):
        data = load_data()
        self.tasks = []
        for t in data.get("tasks", []):
            if isinstance(t, dict) and str(t.get("t", "")).strip():
                self.tasks.append({"t": str(t["t"]), "d": bool(t.get("d", False))})

        self.root = r = tk.Tk()
        r.title("مهامي")
        r.overrideredirect(True)
        r.config(bg=KEY)
        r.attributes("-transparentcolor", KEY)
        r.attributes("-alpha", 0.97)

        self.s = r.winfo_fpixels("1i") / 96.0
        S = self.S
        self.w, self.h = S(W), S(H)
        self.wl = self.w - S(28)            # عرض منطقة القائمة
        self.hl = self.h - S(144) - S(22)   # ارتفاع منطقة القائمة
        self.hover = None
        self.rows = []
        self.content_h = 0
        self.ph = False

        # الموضع المحفوظ (مع التأكد أنه داخل الشاشة)
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        x = data.get("x", sw - self.w - S(40))
        y = data.get("y", S(60))
        try:
            x = max(0, min(int(x), sw - S(80)))
            y = max(0, min(int(y), sh - S(80)))
        except Exception:
            x, y = sw - self.w - S(40), S(60)
        r.geometry(f"{self.w}x{self.h}+{x}+{y}")

        self.f_text = tkfont.Font(family=FAMILY, size=11)
        self.f_done = tkfont.Font(family=FAMILY, size=11, overstrike=True)
        self.line_h = self.f_text.metrics("linespace")

        # ---------- البطاقة ----------
        self.c = c = tk.Canvas(r, width=self.w, height=self.h, bg=KEY, highlightthickness=0, bd=0)
        c.pack()
        rounded_rect(c, 0, 0, self.w - 1, self.h - 1, S(R), fill=BORDER)
        rounded_rect(c, 1, 1, self.w - 2, self.h - 2, S(R) - 1, fill=CARD)

        # ---------- حقل الإدخال ----------
        rounded_rect(c, S(18), S(84), self.w - S(18), S(128), S(22), fill=FIELD)
        px, py = S(40), S(106)
        c.create_oval(px - S(15), py - S(15), px + S(15), py + S(15),
                      fill=ACCENT, outline=ACCENT, tags="plus")
        c.create_line(px - S(6), py, px + S(6), py, fill="#FFFFFF", width=max(2, S(2)),
                      capstyle="round", tags="plus")
        c.create_line(px, py - S(6), px, py + S(6), fill="#FFFFFF", width=max(2, S(2)),
                      capstyle="round", tags="plus")
        c.tag_bind("plus", "<Button-1>", self._plus_click)
        c.tag_bind("plus", "<Enter>", lambda e: c.config(cursor="hand2"))
        c.tag_bind("plus", "<Leave>", lambda e: c.config(cursor=""))

        self.entry = tk.Entry(r, bd=0, relief="flat", bg=FIELD, fg=MUTED,
                              insertbackground=TEXT, highlightthickness=0,
                              font=(FAMILY, 11), justify="right")
        c.create_window(self.w - S(32), py, window=self.entry, anchor="e",
                        width=(self.w - S(32)) - S(62))
        self.entry.bind("<Return>", self._add)
        self.entry.bind("<KP_Enter>", self._add)
        self.entry.bind("<Button-1>", lambda e: self.entry.focus_force())
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self._show_ph()

        # ---------- القائمة ----------
        self.lc = lc = tk.Canvas(r, bg=CARD, highlightthickness=0, bd=0, yscrollincrement=S(24))
        c.create_window(S(14), S(144), window=lc, anchor="nw", width=self.wl, height=self.hl)
        lc.bind("<Motion>", self._on_motion)
        lc.bind("<Leave>", self._on_leave)
        lc.bind("<Button-1>", self._on_click)
        r.bind_all("<MouseWheel>", self._on_wheel)

        # ---------- سحب النافذة ----------
        c.bind("<Button-1>", self._drag_start)
        c.bind("<B1-Motion>", self._drag_move)
        c.bind("<ButtonRelease-1>", lambda e: self._save())

        # ---------- قائمة كليك يمين ----------
        self.top = tk.BooleanVar(value=bool(data.get("top", False)))
        r.attributes("-topmost", self.top.get())
        self.menu = tk.Menu(r, tearoff=0, font=(FAMILY, 10))
        self.menu.add_checkbutton(label="تثبيت فوق النوافذ", variable=self.top,
                                  command=self._toggle_top)
        self.menu.add_command(label="حذف المهام المكتملة", command=self._clear_done)
        self.menu.add_separator()
        self.menu.add_command(label="إغلاق", command=self._quit)
        c.bind("<Button-3>", self._popup)
        lc.bind("<Button-3>", self._popup)

        self._refresh()

    # ---------- أدوات ----------
    def S(self, v):
        return int(round(v * self.s))

    def _save(self):
        save_data({"x": self.root.winfo_x(), "y": self.root.winfo_y(),
                   "top": bool(self.top.get()), "tasks": self.tasks})

    def _quit(self):
        self._save()
        self.root.destroy()

    def _popup(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    def _toggle_top(self):
        self.root.attributes("-topmost", self.top.get())
        self._save()

    def _drag_start(self, e):
        self._ox, self._oy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._ox
        y = self.root.winfo_y() + e.y - self._oy
        self.root.geometry(f"+{x}+{y}")

    # ---------- حقل الإدخال ----------
    def _show_ph(self):
        self.ph = True
        self.entry.delete(0, "end")
        self.entry.insert(0, PLACEHOLDER)
        self.entry.config(fg=MUTED)

    def _focus_in(self, _=None):
        if self.ph:
            self.entry.delete(0, "end")
            self.entry.config(fg=TEXT)
            self.ph = False

    def _focus_out(self, _=None):
        if not self.entry.get().strip():
            self._show_ph()

    def _plus_click(self, _=None):
        self.entry.focus_force()
        self._add()

    def _add(self, _=None):
        text = "" if self.ph else self.entry.get().strip()
        if not text:
            return
        self.tasks.insert(0, {"t": text[:200], "d": False})
        self.entry.delete(0, "end")
        self.hover = None
        self._refresh()
        self.lc.yview_moveto(0)
        self._save()

    # ---------- العمليات على المهام ----------
    def _toggle(self, i):
        self.tasks[i]["d"] = not self.tasks[i]["d"]
        self.hover = None
        self._refresh()
        self._save()

    def _delete(self, i):
        del self.tasks[i]
        self.hover = None
        self._refresh()
        self._save()

    def _clear_done(self):
        self.tasks = [t for t in self.tasks if not t["d"]]
        self.hover = None
        self._refresh()
        self._save()

    # ---------- أحداث القائمة ----------
    def _row_at(self, y):
        for row in self.rows:
            if row["y0"] <= y < row["y1"]:
                return row
        return None

    def _on_motion(self, e):
        row = self._row_at(self.lc.canvasy(e.y))
        idx = row["i"] if row else None
        if idx != self.hover:
            self.hover = idx
            self.lc.config(cursor="hand2" if idx is not None else "")
            self._draw_list()

    def _on_leave(self, _=None):
        if self.hover is not None:
            self.hover = None
            self._draw_list()

    def _on_click(self, e):
        row = self._row_at(self.lc.canvasy(e.y))
        if not row:
            return
        if e.x < self.S(46):
            self._delete(row["i"])
        else:
            self._toggle(row["i"])

    def _on_wheel(self, e):
        try:
            if self.root.winfo_containing(e.x_root, e.y_root) is not self.lc:
                return
        except Exception:
            return
        if self.content_h > self.hl:
            self.lc.yview_scroll(-2 if e.delta > 0 else 2, "units")

    # ---------- الرسم ----------
    def _refresh(self):
        self._draw_header()
        self._draw_list()

    def _draw_header(self):
        c, S, w = self.c, self.S, self.w
        c.delete("hdr")
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["d"])

        c.create_text(w - S(26), S(40), text="مهامي", anchor="e", fill=TEXT,
                      font=(FAMILY + " Semibold", 20), tags="hdr")
        if total:
            if done == total:
                txt, col = "أنجزت كل المهام", ACCENT
            else:
                txt, col = f"{ar(done)} من {ar(total)}", MUTED
            c.create_text(S(26), S(44), text=txt, anchor="w", fill=col,
                          font=(FAMILY, 10), tags="hdr")

        x1, x2, y = S(28), w - S(28), S(68)
        c.create_line(x1, y, x2, y, fill=BORDER, width=S(4), capstyle="round", tags="hdr")
        if total and done:
            xs = x2 - (x2 - x1) * done / total
            c.create_line(xs, y, x2, y, fill=ACCENT, width=S(4), capstyle="round", tags="hdr")

    def _wrap(self, text, maxw, maxlines=3):
        f = self.f_text
        lines, cur = [], ""
        for wd in text.split():
            trial = (cur + " " + wd).strip()
            if f.measure(trial) <= maxw:
                cur = trial
                continue
            if cur:
                lines.append(cur)
                cur = ""
            while f.measure(wd) > maxw and len(wd) > 1:
                k = len(wd)
                while k > 1 and f.measure(wd[:k]) > maxw:
                    k -= 1
                lines.append(wd[:k])
                wd = wd[k:]
            cur = wd
        if cur:
            lines.append(cur)
        if not lines:
            lines = [text]
        if len(lines) > maxlines:
            lines = lines[:maxlines]
            last = lines[-1]
            while last and f.measure(last + "…") > maxw:
                last = last[:-1]
            lines[-1] = last.rstrip() + "…"
        return lines

    def _draw_list(self):
        lc, S, wl, s = self.lc, self.S, self.wl, self.s
        lc.delete("all")
        self.rows = []

        if not self.tasks:
            self.content_h = 0
            lc.configure(scrollregion=(0, 0, wl, self.hl))
            lc.create_text(wl // 2, self.hl // 2 - S(14), text="لا توجد مهام", fill=MUTED,
                           font=(FAMILY + " Semibold", 13))
            lc.create_text(wl // 2, self.hl // 2 + S(14), text="اكتب مهمة واضغط Enter",
                           fill=RING, font=(FAMILY, 10))
            return

        order = sorted(range(len(self.tasks)), key=lambda i: self.tasks[i]["d"])
        right = wl - S(50)
        maxw = right - S(48)
        y = 0
        for i in order:
            task = self.tasks[i]
            lines = self._wrap(task["t"], maxw)
            nl = len(lines)
            rh = max(S(48), 2 * S(13) + nl * self.line_h)
            self.rows.append({"i": i, "y0": y, "y1": y + rh})
            hov = (self.hover == i)

            if hov:
                rounded_rect(lc, S(2), y + S(2), wl - S(2), y + rh - S(2), S(12), fill=HOVER)
            else:
                lc.create_line(S(12), y + rh - 1, wl - S(12), y + rh - 1, fill=LINE)

            top = y + (rh - nl * self.line_h) / 2
            cx, cy, rad = wl - S(26), top + self.line_h / 2, S(10)
            if task["d"]:
                lc.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill=ACCENT, outline=ACCENT)
                lc.create_line(cx - 4.5 * s, cy, cx - 1.2 * s, cy + 3.5 * s, cx + 4.8 * s, cy - 3.5 * s,
                               fill="#FFFFFF", width=max(2, S(2)), capstyle="round", joinstyle="round")
            else:
                lc.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                               outline=ACCENT if hov else RING, width=max(2, S(2)))

            for k, ln in enumerate(lines):
                lc.create_text(right, top + k * self.line_h + self.line_h / 2, text=ln, anchor="e",
                               fill=MUTED if task["d"] else TEXT,
                               font=self.f_done if task["d"] else self.f_text)

            if hov:
                dx = S(24)
                lc.create_line(dx - S(5), cy - S(5), dx + S(5), cy + S(5), fill=MUTED,
                               width=max(2, S(2)), capstyle="round")
                lc.create_line(dx - S(5), cy + S(5), dx + S(5), cy - S(5), fill=MUTED,
                               width=max(2, S(2)), capstyle="round")
            y += rh

        self.content_h = y
        lc.configure(scrollregion=(0, 0, wl, max(y, self.hl)))
        if y <= self.hl:
            lc.yview_moveto(0)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TodoWidget().run()
