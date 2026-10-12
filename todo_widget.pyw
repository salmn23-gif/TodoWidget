# -*- coding: utf-8 -*-
"""
ودجت قائمة المهام - سطح مكتب ويندوز 11
- اكتب المهمة ثم Enter (أو زر +)
- انقر على المهمة لإنجازها، ومرّر الفأرة فوقها لتظهر علامة الحذف
- اسحب الودجت من أي مكان فارغ لتحريكه (يُحفظ مكانه)
- كليك يمين: الإعدادات (الحجم والألوان والشفافية) / تثبيت فوق النوافذ / حذف المكتملة / إغلاق
- بدون أي مكتبات خارجية
"""
import ctypes
import json
import os
import re
import tkinter as tk
from tkinter import colorchooser
from tkinter import font as tkfont

# ---------- وضوح الخطوط على الشاشات عالية الدقة ----------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

KEY = "#010203"            # لون الشفافية (لا يظهر)
FAMILY = "Segoe UI"
W, H, R = 330, 480, 26
PLACEHOLDER = "أضف مهمة جديدة…"
AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
CONFIG = os.path.join(os.path.expanduser("~"), ".todo_widget.json")

DEFAULTS = {"zoom": 1.0, "bg": "#15171E", "accent": "#6C8CFF", "alpha": 0.97}
BG_PRESETS = ["#15171E", "#0A0B0F", "#0F172A", "#1E1B2E", "#132520", "#F5F6FA"]
ACCENT_PRESETS = ["#6C8CFF", "#34D399", "#A78BFA", "#F472B6", "#FB923C", "#22D3EE", "#F87171"]

# ألوان نافذة الإعدادات (ثابتة)
SB, SF, SM, SBTN = "#1B1D25", "#F1F3F7", "#8B93A3", "#2A2D38"


# ---------- ألوان ----------
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c):
    return "#%02x%02x%02x" % tuple(int(round(max(0, min(255, v)))) for v in c)


def mix(a, b, t):
    ra, rb = hex_rgb(a), hex_rgb(b)
    return rgb_hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def lum(h):
    r, g, b = hex_rgb(h)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def clean_hex(v, default):
    return v if isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v) else default


def clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return default


def make_theme(bg, accent):
    dark = lum(bg) < 0.5
    hi = "#FFFFFF" if dark else "#000000"
    return {
        "card": bg,
        "border": mix(bg, hi, 0.10),
        "hover": mix(bg, hi, 0.04),
        "line": mix(bg, hi, 0.06),
        "ring": mix(bg, hi, 0.30),
        "muted": mix(bg, hi, 0.52),
        "field": mix(bg, hi, 0.05) if dark else mix(bg, "#FFFFFF", 0.65),
        "text": "#F1F3F7" if dark else "#171A21",
        "accent": accent,
        "on_accent": "#FFFFFF" if lum(accent) < 0.62 else "#14161C",
    }


# ---------- رسم أيقونات عالية الدقة (تنعيم الحواف بأخذ عيّنات متعددة) ----------
def render_pixels(n, bg, layers, ss=4):
    """يرجع n صفاً من ألوان hex. layers: ('disc',cx,cy,r,col) / ('ring',cx,cy,ro,ri,col) / ('line',x1,y1,x2,y2,hw,col)"""
    bgc = hex_rgb(bg)
    L = []
    for ly in layers:
        k = ly[0]
        if k == "disc":
            L.append((0, ly[1], ly[2], ly[3] ** 2, 0, hex_rgb(ly[4])))
        elif k == "ring":
            L.append((1, ly[1], ly[2], ly[3] ** 2, ly[4] ** 2, hex_rgb(ly[5])))
        else:
            L.append((2, ly[1], ly[2], ly[3], ly[4], ly[5] ** 2, hex_rgb(ly[6])))
    inv = 1.0 / (ss * ss)
    rows = []
    for y in range(n):
        row = []
        for x in range(n):
            ar_ = ag = ab = 0
            for sy in range(ss):
                py = y + (sy + 0.5) / ss
                for sx in range(ss):
                    px = x + (sx + 0.5) / ss
                    col = bgc
                    for t in L:
                        k = t[0]
                        if k == 0:
                            if (px - t[1]) ** 2 + (py - t[2]) ** 2 <= t[3]:
                                col = t[5]
                        elif k == 1:
                            d = (px - t[1]) ** 2 + (py - t[2]) ** 2
                            if t[4] <= d <= t[3]:
                                col = t[5]
                        else:
                            x1, y1, x2, y2 = t[1], t[2], t[3], t[4]
                            dx, dy = x2 - x1, y2 - y1
                            ll = dx * dx + dy * dy
                            u = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ll))
                            qx, qy = x1 + u * dx - px, y1 + u * dy - py
                            if qx * qx + qy * qy <= t[5]:
                                col = t[6]
                    ar_ += col[0]
                    ag += col[1]
                    ab += col[2]
            row.append(rgb_hex((ar_ * inv, ag * inv, ab * inv)))
        rows.append(row)
    return rows


def make_image(master, n, bg, layers):
    rows = render_pixels(n, bg, layers)
    img = tk.PhotoImage(master=master, width=n, height=n)
    img.put(" ".join("{" + " ".join(r) + "}" for r in rows))
    return img


# ---------- الحفظ ----------
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


def ar(n):
    return str(n).translate(AR)


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

        self.zoom = clamp(data.get("zoom", DEFAULTS["zoom"]), 0.7, 1.5, 1.0)
        self.bg = clean_hex(data.get("bg"), DEFAULTS["bg"])
        self.accent = clean_hex(data.get("accent"), DEFAULTS["accent"])
        self.alpha = clamp(data.get("alpha", DEFAULTS["alpha"]), 0.6, 1.0, 0.97)

        self.root = r = tk.Tk()
        r.title("مهامي")
        r.overrideredirect(True)
        r.config(bg=KEY)
        r.attributes("-transparentcolor", KEY)

        self.dpi = r.winfo_fpixels("1i") / 96.0
        self.s = self.dpi * self.zoom
        self.cache = {}
        self.win = None
        self._zoom_job = None
        self.hover = None
        self.rows = []
        self.content_h = 0
        self.ph = True
        self.c = self.lc = self.entry = self.menu = None

        self.top = tk.BooleanVar(value=bool(data.get("top", False)))
        r.attributes("-topmost", self.top.get())
        r.bind_all("<MouseWheel>", self._on_wheel)

        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        x = data.get("x", sw - int(370 * self.s))
        y = data.get("y", int(60 * self.s))
        try:
            pos = (int(x), int(y))
        except Exception:
            pos = (sw - int(370 * self.s), int(60 * self.s))
        self._build(pos)

    # ---------- أدوات ----------
    def S(self, v):
        return int(round(v * self.s))

    def F(self, size):
        return max(7, int(round(size * self.zoom)))

    def _save(self):
        save_data({"x": self.root.winfo_x(), "y": self.root.winfo_y(),
                   "top": bool(self.top.get()), "zoom": self.zoom, "bg": self.bg,
                   "accent": self.accent, "alpha": self.alpha, "tasks": self.tasks})

    def _quit(self):
        self._save()
        self.root.destroy()

    def _icon(self, key, n, bg, layers):
        t = self.t
        k = (key, n, bg, t["accent"], t["ring"], t["muted"], t["on_accent"])
        if k not in self.cache:
            self.cache[k] = make_image(self.root, n, bg, layers)
        return self.cache[k]

    def _make_icons(self):
        t, s, S = self.t, self.s, self.S
        ic = {}

        # زر +
        n = S(34)
        c = n / 2.0
        a = 0.22 * n
        hw = max(1.1, 0.055 * n)
        ic["plus"] = self._icon("plus", n, t["field"], [
            ("disc", c, c, c - 1, t["accent"]),
            ("line", c - a, c, c + a, c, hw, t["on_accent"]),
            ("line", c, c - a, c, c + a, hw, t["on_accent"]),
        ])

        # دائرة الإنجاز
        n = 2 * S(11)
        c = n / 2.0
        ro = S(10)
        thick = max(1.8, 2.0 * s)
        hwc = max(1.0, 1.1 * s)
        p1 = (c - 4.5 * s, c)
        p2 = (c - 1.2 * s, c + 3.5 * s)
        p3 = (c + 4.8 * s, c - 3.5 * s)
        for name, bg in (("card", t["card"]), ("hover", t["hover"])):
            ic["done_" + name] = self._icon("done_" + name, n, bg, [
                ("disc", c, c, ro, t["accent"]),
                ("line", p1[0], p1[1], p2[0], p2[1], hwc, t["on_accent"]),
                ("line", p2[0], p2[1], p3[0], p3[1], hwc, t["on_accent"]),
            ])
        ic["ring_card"] = self._icon("ring_card", n, t["card"], [
            ("ring", c, c, ro, ro - thick, t["ring"])])
        ic["ring_hover"] = self._icon("ring_hover", n, t["hover"], [
            ("ring", c, c, ro, ro - thick, t["accent"])])

        # علامة الحذف
        n = 2 * S(8)
        c = n / 2.0
        d = 4.6 * s
        hwx = max(1.0, 1.0 * s)
        ic["cross"] = self._icon("cross", n, t["hover"], [
            ("line", c - d, c - d, c + d, c + d, hwx, t["muted"]),
            ("line", c - d, c + d, c + d, c - d, hwx, t["muted"]),
        ])
        return ic

    # ---------- بناء الواجهة (يُعاد عند تغيير الحجم أو اللون) ----------
    def _build(self, pos):
        r = self.root
        entry_text, entry_ph = ("", True)
        if self.entry is not None:
            entry_ph = self.ph
            entry_text = "" if self.ph else self.entry.get()
        for name in ("lc", "entry", "c", "menu"):
            w = getattr(self, name)
            if w is not None:
                try:
                    w.destroy()
                except Exception:
                    pass
                setattr(self, name, None)

        self.s = self.dpi * self.zoom
        S = self.S
        self.t = t = make_theme(self.bg, self.accent)
        self.w, self.h = S(W), S(H)
        self.wl = self.w - S(28)
        self.hl = self.h - S(144) - S(22)
        self.hover = None

        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        x = max(0, min(int(pos[0]), sw - self.w))
        y = max(0, min(int(pos[1]), sh - self.h))
        r.geometry(f"{self.w}x{self.h}+{x}+{y}")
        r.attributes("-alpha", self.alpha)

        self.f_text = tkfont.Font(family=FAMILY, size=self.F(11))
        self.f_done = tkfont.Font(family=FAMILY, size=self.F(11), overstrike=True)
        self.line_h = self.f_text.metrics("linespace")
        self.icons = self._make_icons()

        # ---------- البطاقة ----------
        self.c = c = tk.Canvas(r, width=self.w, height=self.h, bg=KEY, highlightthickness=0, bd=0)
        c.pack()
        rounded_rect(c, 0, 0, self.w - 1, self.h - 1, S(R), fill=t["border"])
        rounded_rect(c, 1, 1, self.w - 2, self.h - 2, S(R) - 1, fill=t["card"])

        # ---------- حقل الإدخال ----------
        rounded_rect(c, S(18), S(84), self.w - S(18), S(128), S(22), fill=t["field"])
        px, py = S(40), S(106)
        c.create_image(px, py, image=self.icons["plus"], tags="plus")
        c.tag_bind("plus", "<Button-1>", self._plus_click)
        c.tag_bind("plus", "<Enter>", lambda e: c.config(cursor="hand2"))
        c.tag_bind("plus", "<Leave>", lambda e: c.config(cursor=""))

        self.entry = tk.Entry(r, bd=0, relief="flat", bg=t["field"], fg=t["muted"],
                              insertbackground=t["text"], highlightthickness=0,
                              font=(FAMILY, self.F(11)), justify="right")
        c.create_window(self.w - S(32), py, window=self.entry, anchor="e",
                        width=(self.w - S(32)) - S(62))
        self.entry.bind("<Return>", self._add)
        self.entry.bind("<KP_Enter>", self._add)
        self.entry.bind("<Button-1>", lambda e: self.entry.focus_force())
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        if entry_ph or not entry_text:
            self._show_ph()
        else:
            self.ph = False
            self.entry.insert(0, entry_text)
            self.entry.config(fg=t["text"])

        # ---------- القائمة ----------
        self.lc = lc = tk.Canvas(r, bg=t["card"], highlightthickness=0, bd=0, yscrollincrement=S(24))
        c.create_window(S(14), S(144), window=lc, anchor="nw", width=self.wl, height=self.hl)
        lc.bind("<Motion>", self._on_motion)
        lc.bind("<Leave>", self._on_leave)
        lc.bind("<Button-1>", self._on_click)

        # ---------- سحب النافذة ----------
        c.bind("<Button-1>", self._drag_start)
        c.bind("<B1-Motion>", self._drag_move)
        c.bind("<ButtonRelease-1>", lambda e: self._save())

        # ---------- قائمة كليك يمين ----------
        self.menu = tk.Menu(r, tearoff=0, font=(FAMILY, 10))
        self.menu.add_command(label="الإعدادات…", command=self._open_settings)
        self.menu.add_checkbutton(label="تثبيت فوق النوافذ", variable=self.top,
                                  command=self._toggle_top)
        self.menu.add_command(label="حذف المهام المكتملة", command=self._clear_done)
        self.menu.add_separator()
        self.menu.add_command(label="إغلاق", command=self._quit)
        c.bind("<Button-3>", self._popup)
        lc.bind("<Button-3>", self._popup)

        self._refresh()

    def _rebuild(self):
        self._build((self.root.winfo_x(), self.root.winfo_y()))
        self._save()

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
        self.entry.config(fg=self.t["muted"])

    def _focus_in(self, _=None):
        if self.ph:
            self.entry.delete(0, "end")
            self.entry.config(fg=self.t["text"])
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
            if self.lc is None or self.root.winfo_containing(e.x_root, e.y_root) is not self.lc:
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
        c, S, w, t = self.c, self.S, self.w, self.t
        c.delete("hdr")
        total = len(self.tasks)
        done = sum(1 for x in self.tasks if x["d"])

        c.create_text(w - S(26), S(40), text="مهامي", anchor="e", fill=t["text"],
                      font=(FAMILY + " Semibold", self.F(20)), tags="hdr")
        if total:
            if done == total:
                txt, col = "أنجزت كل المهام", t["accent"]
            else:
                txt, col = f"{ar(done)} من {ar(total)}", t["muted"]
            c.create_text(S(26), S(44), text=txt, anchor="w", fill=col,
                          font=(FAMILY, self.F(10)), tags="hdr")

        x1, x2, y = S(28), w - S(28), S(68)
        c.create_line(x1, y, x2, y, fill=t["border"], width=S(4), capstyle="round", tags="hdr")
        if total and done:
            xs = x2 - (x2 - x1) * done / total
            c.create_line(xs, y, x2, y, fill=t["accent"], width=S(4), capstyle="round", tags="hdr")

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
        lc, S, wl, t = self.lc, self.S, self.wl, self.t
        lc.delete("all")
        self.rows = []

        if not self.tasks:
            self.content_h = 0
            lc.configure(scrollregion=(0, 0, wl, self.hl))
            lc.create_text(wl // 2, self.hl // 2 - S(14), text="لا توجد مهام", fill=t["muted"],
                           font=(FAMILY + " Semibold", self.F(13)))
            lc.create_text(wl // 2, self.hl // 2 + S(14), text="اكتب مهمة واضغط Enter",
                           fill=t["ring"], font=(FAMILY, self.F(10)))
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
                rounded_rect(lc, S(2), y + S(2), wl - S(2), y + rh - S(2), S(12), fill=t["hover"])
            else:
                lc.create_line(S(12), y + rh - 1, wl - S(12), y + rh - 1, fill=t["line"])

            top = y + (rh - nl * self.line_h) / 2
            cx, cy = wl - S(26), top + self.line_h / 2
            bgk = "hover" if hov else "card"
            if task["d"]:
                lc.create_image(cx, cy, image=self.icons["done_" + bgk])
            else:
                lc.create_image(cx, cy, image=self.icons["ring_hover" if hov else "ring_card"])

            for k, ln in enumerate(lines):
                lc.create_text(right, top + k * self.line_h + self.line_h / 2, text=ln, anchor="e",
                               fill=t["muted"] if task["d"] else t["text"],
                               font=self.f_done if task["d"] else self.f_text)

            if hov:
                lc.create_image(S(24), cy, image=self.icons["cross"])
            y += rh

        self.content_h = y
        lc.configure(scrollregion=(0, 0, wl, max(y, self.hl)))
        if y <= self.hl:
            lc.yview_moveto(0)

    # ---------- نافذة الإعدادات ----------
    def _swatch(self, col, selected):
        d = self.dpi
        n = int(30 * d)
        k = ("sw", col, selected, n)
        if k not in self.cache:
            c = n / 2.0
            ro = c - 1
            ri = ro - max(1.6, 0.075 * n)
            rd = ri - max(1.2, 0.06 * n)
            layers = []
            if selected:
                layers.append(("ring", c, c, ro, ri, "#FFFFFF"))
            layers.append(("disc", c, c, rd, col))
            self.cache[k] = make_image(self.root, n, SB, layers)
        return self.cache[k]

    def _open_settings(self):
        if self.win is not None:
            try:
                if self.win.winfo_exists():
                    self.win.lift()
                    self.win.focus_force()
                    return
            except Exception:
                pass

        d = self.dpi
        pad = int(16 * d)
        win = tk.Toplevel(self.root)
        self.win = win
        win.title("إعدادات الودجت")
        win.configure(bg=SB)
        win.resizable(False, False)
        win.attributes("-topmost", True)

        def section(title):
            f = tk.Frame(win, bg=SB)
            f.pack(fill="x", padx=pad, pady=(pad, 0))
            tk.Label(f, text=title, bg=SB, fg=SM, font=(FAMILY, 10), anchor="e").pack(fill="x")
            return f

        def make_scale(parent, lo, hi, val, command):
            sc = tk.Scale(parent, from_=lo, to=hi, resolution=5, orient="horizontal",
                          length=int(300 * d), bg=SB, fg=SF, troughcolor=SBTN,
                          highlightthickness=0, bd=0, sliderrelief="flat",
                          activebackground=SM, font=(FAMILY, 9), command=command)
            sc.set(val)
            sc.pack(fill="x", pady=(4, 0))
            return sc

        # الحجم
        f = section("الحجم")

        def zoom_changed(v):
            v = int(float(v))
            if v == int(round(self.zoom * 100)):
                return
            if self._zoom_job:
                self.root.after_cancel(self._zoom_job)
            self._zoom_job = self.root.after(300, lambda: self._set_zoom(v / 100.0))

        make_scale(f, 70, 150, int(round(self.zoom * 100)), zoom_changed)

        # الألوان
        def swatch_row(title, presets, get, set_):
            f = section(title)
            line = tk.Frame(f, bg=SB)
            line.pack(anchor="e", pady=(6, 0))
            items = []

            def refresh():
                for lbl, col in items:
                    lbl.config(image=self._swatch(col, col.lower() == get().lower()))

            def pick(col):
                set_(col)
                refresh()

            for col in presets:
                lbl = tk.Label(line, bg=SB, bd=0, cursor="hand2")
                lbl.pack(side="right", padx=int(2 * d))
                lbl.bind("<Button-1>", lambda e, c=col: pick(c))
                items.append((lbl, col))

            def custom():
                res = colorchooser.askcolor(color=get(), parent=win, title="اختر لوناً")
                if res and res[1]:
                    pick(res[1])

            tk.Button(line, text="مخصص…", command=custom, bg=SBTN, fg=SF, bd=0, relief="flat",
                      activebackground="#343846", activeforeground=SF, cursor="hand2",
                      font=(FAMILY, 9), padx=int(8 * d)).pack(side="right", padx=(int(8 * d), 0))
            refresh()

        swatch_row("لون الخلفية", BG_PRESETS, lambda: self.bg, self._set_bg)
        swatch_row("لون التمييز", ACCENT_PRESETS, lambda: self.accent, self._set_accent)

        # الشفافية
        f = section("الشفافية")

        def alpha_changed(v):
            self.alpha = int(float(v)) / 100.0
            self.root.attributes("-alpha", self.alpha)

        sc = make_scale(f, 60, 100, int(round(self.alpha * 100)), alpha_changed)
        sc.bind("<ButtonRelease-1>", lambda e: self._save())

        # أزرار
        bar = tk.Frame(win, bg=SB)
        bar.pack(fill="x", padx=pad, pady=pad)

        def close():
            self._save()
            win.destroy()

        def reset():
            self.zoom = DEFAULTS["zoom"]
            self.bg = DEFAULTS["bg"]
            self.accent = DEFAULTS["accent"]
            self.alpha = DEFAULTS["alpha"]
            self._rebuild()
            win.destroy()
            self._open_settings()

        tk.Button(bar, text="تم", command=close, bg=self.accent, fg=self.t["on_accent"], bd=0,
                  relief="flat", cursor="hand2", font=(FAMILY, 10, "bold"),
                  padx=int(22 * d), pady=int(4 * d)).pack(side="right")
        tk.Button(bar, text="إعادة الضبط", command=reset, bg=SBTN, fg=SF, bd=0, relief="flat",
                  activebackground="#343846", activeforeground=SF, cursor="hand2",
                  font=(FAMILY, 10), padx=int(14 * d), pady=int(4 * d)).pack(side="right", padx=int(8 * d))
        win.protocol("WM_DELETE_WINDOW", close)

        # مكان النافذة بجانب الودجت
        win.update_idletasks()
        ww, wh = win.winfo_reqwidth(), win.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        x = self.root.winfo_x() - ww - int(16 * d)
        if x < 0:
            x = min(self.root.winfo_x() + self.w + int(16 * d), max(0, sw - ww))
        win.geometry(f"+{x}+{max(0, self.root.winfo_y())}")

    def _set_zoom(self, z):
        self._zoom_job = None
        self.zoom = max(0.7, min(1.5, z))
        self._rebuild()

    def _set_bg(self, col):
        self.bg = clean_hex(col, self.bg)
        self._rebuild()

    def _set_accent(self, col):
        self.accent = clean_hex(col, self.accent)
        self._rebuild()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TodoWidget().run()
