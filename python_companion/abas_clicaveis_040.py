"""Duas pequenas janelas interativas; o restante do painel mantém click-through."""
import ctypes as C
from ctypes import wintypes as W
import logging
import sys
import tkinter as tk
from tkinter import font as tkfont
TABS = ('Economia', 'Militar')

def tab_regions(width):
    size = max(72, min(112, (width - 16) // 3))
    return [(8 + i * (size + 4), 6, size + 1, 24, tab) for i, tab in enumerate(TABS)]

class Windows:

    def __init__(self, library=None):
        self.u = library or C.WinDLL('user32', use_last_error=True)
        self.setptr = getattr(self.u, 'SetWindowLongPtrW', self.u.SetWindowLongW)
        self.setptr.argtypes = [W.HWND, C.c_int, C.c_void_p]
        self.setptr.restype = C.c_void_p
        self.u.GetWindowLongW.argtypes = [W.HWND, C.c_int]
        self.u.GetWindowLongW.restype = C.c_long
        self.u.SetWindowLongW.argtypes = [W.HWND, C.c_int, C.c_long]
        self.u.SetWindowLongW.restype = C.c_long
        self.u.CallWindowProcW.argtypes = [C.c_void_p, W.HWND, W.UINT, C.c_size_t, C.c_ssize_t]
        self.u.CallWindowProcW.restype = C.c_ssize_t
        self.u.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
        self.u.GetWindowRect.restype = W.BOOL
        self.u.GetForegroundWindow.argtypes = []
        self.u.GetForegroundWindow.restype = W.HWND
        self.u.SetForegroundWindow.argtypes = [W.HWND]
        self.u.SetForegroundWindow.restype = W.BOOL
        self.u.IsWindow.argtypes = [W.HWND]
        self.u.IsWindow.restype = W.BOOL
        self.u.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
        self.u.SetWindowPos.restype = W.BOOL
        factory = getattr(C, 'WINFUNCTYPE', C.CFUNCTYPE)
        self.proc_type = factory(C.c_ssize_t, W.HWND, W.UINT, C.c_size_t, C.c_ssize_t)
        self.hooks = {}

    def style(self, hwnd):
        current = self.u.GetWindowLongW(hwnd, -20)
        desired = (current | 134217728 | 128 | 524288) & ~(32 | 262144)
        self.u.SetWindowLongW(hwnd, -20, desired)

    def attach(self, hwnd):
        self.style(hwnd)
        holder = {}

        def callback(handle, message, wparam, lparam):
            if message == 33:
                return 3
            return self.u.CallWindowProcW(holder['original'], handle, message, wparam, lparam)
        proc = self.proc_type(callback)
        original = self.setptr(hwnd, -4, C.cast(proc, C.c_void_p))
        if not original:
            raise RuntimeError('Não foi possível preparar a aba sem ativar a janela.')
        holder['original'] = original
        self.hooks[hwnd] = (original, proc)

    def detach(self, hwnd):
        record = self.hooks.get(hwnd)
        if record and self.u.IsWindow(hwnd):
            self.setptr(hwnd, -4, record[0])
        self.hooks.pop(hwnd, None)

    def rect(self, hwnd):
        area = W.RECT()
        if not self.u.GetWindowRect(hwnd, C.byref(area)):
            raise RuntimeError('Não foi possível localizar o painel.')
        return (area.left, area.top, area.right - area.left, area.bottom - area.top)

    def keep_focus(self, previous, tabs):
        current = self.u.GetForegroundWindow()
        if previous and current != previous and (current in tabs):
            self.u.SetForegroundWindow(previous)

    def move(self, hwnd, x, y, width, height):
        self.style(hwnd)
        self.u.SetWindowPos(hwnd, C.c_void_p(-1), x, y, width, height, 80)

class ClickTabs:

    def __init__(self, owner):
        self.owner = owner
        self.items = []
        self.closed = False
        self.api = Windows() if sys.platform == 'win32' else None
        try:
            for tab in TABS:
                popup = tk.Toplevel(owner.root)
                popup.withdraw()
                popup.overrideredirect(True)
                popup.attributes('-topmost', True)
                popup.attributes('-alpha', 0.01)
                canvas = tk.Canvas(popup, bd=0, highlightthickness=0, cursor='hand2', takefocus=False)
                canvas.pack(fill='both', expand=True)
                item = {'window': popup, 'canvas': canvas, 'tab': tab, 'hover': False, 'pressed': False, 'key': None, 'hwnd': None}
                self.items.append(item)
                popup.update_idletasks()
                if self.api:
                    item['hwnd'] = owner.native.u.GetAncestor(popup.winfo_id(), 2)
                    self.api.attach(item['hwnd'])
                canvas.bind('<Enter>', lambda event, a=item: self.hover(a, True))
                canvas.bind('<Leave>', lambda event, a=item: self.hover(a, False))
                canvas.bind('<ButtonPress-1>', lambda event, a=item: self.press(a))
                canvas.bind('<ButtonRelease-1>', lambda event, a=item: self.release(a, event))
            owner.root.bind('<Destroy>', self.destroyed, add='+')
        except Exception:
            self.close()
            raise

    def destroyed(self, event):
        if event.widget is self.owner.root:
            self.close()

    def hide(self):
        if getattr(self.owner, '_click_tab_hover', None) is not None or getattr(self.owner, '_click_tab_pressed', None) is not None:
            self.owner._click_tab_hover = None
            self.owner._click_tab_pressed = None
            self.owner.bar_cache = None
        for item in self.items:
            item['pressed'] = False
            item['hover'] = False
            item['key'] = None
            item['place'] = None
            if item['window'].winfo_exists() and item['window'].state() != 'withdrawn':
                item['window'].withdraw()

    def sync(self):
        if self.closed:
            return
        if self.owner.closing or not self.owner.caption.winfo_ismapped():
            self.hide()
            return
        if self.api:
            x, y, width, height = self.api.rect(self.owner.caption_hwnd)
        else:
            caption = self.owner.caption
            x, y, width, height = (caption.winfo_rootx(), caption.winfo_rooty(), caption.winfo_width(), caption.winfo_height())
        previous = self.api.u.GetForegroundWindow() if self.api else None
        for item, region in zip(self.items, tab_regions(width)):
            left, top, w, h, tab = region
            popup = item['window']
            opacity = 0.01
            if popup.attributes('-alpha') != opacity:
                popup.attributes('-alpha', opacity)
                if self.api:
                    self.api.style(item['hwnd'])
            place = (x + left, y + top, w, h)
            if item.get('place') != place or popup.state() == 'withdrawn':
                popup.geometry(f'{w}x{h}{x + left:+d}{y + top:+d}')
                if popup.state() == 'withdrawn':
                    popup.deiconify()
                if self.api:
                    self.api.move(item['hwnd'], *place)
                popup.update_idletasks()
                item['place'] = place
            self.draw(item)
        if self.api:
            self.api.keep_focus(previous, {item['hwnd'] for item in self.items})

    def close(self):
        if self.closed:
            return
        self.closed = True
        for item in self.items:
            if self.api and item['hwnd']:
                self.api.detach(item['hwnd'])
            try:
                if item['window'].winfo_exists():
                    item['window'].destroy()
            except tk.TclError:
                pass

    def refresh_visual(self):
        if not self.closed and (not self.owner.closing):
            self.owner.bar_cache = None
            self.owner.update_horizontal_panel()

    def hover(self, item, value):
        item['hover'] = value
        if value:
            self.owner._click_tab_hover = item['tab']
        elif getattr(self.owner, '_click_tab_hover', None) == item['tab']:
            self.owner._click_tab_hover = None
        self.refresh_visual()
        return 'break'

    def press(self, item):
        item['pressed'] = True
        self.owner._click_tab_pressed = item['tab']
        self.refresh_visual()
        return 'break'

    def release(self, item, event):
        pressed = item['pressed']
        item['pressed'] = False
        self.owner._click_tab_pressed = None
        canvas = item['canvas']
        if pressed and 0 <= event.x < canvas.winfo_width() and (0 <= event.y < canvas.winfo_height()):
            self.owner.panel_tab.set(item['tab'])
        self.refresh_visual()
        return 'break'

    def draw(self, item):
        if item.get('key') != 'hotspot':
            item['canvas'].delete('all')
            item['canvas'].configure(bg='black')
            item['key'] = 'hotspot'

def sync(owner):
    manager = getattr(owner, '_click_tab_manager', None)
    if owner.closing:
        if manager:
            manager.hide()
        return
    if manager is None:
        if not owner.caption.winfo_ismapped():
            return
        if getattr(owner, '_click_tabs_failed', False):
            return
        try:
            manager = ClickTabs(owner)
            owner._click_tab_manager = manager
        except Exception as error:
            owner._click_tabs_active = False
            owner._click_tabs_failed = True
            owner.bar_cache = None
            owner.status.set('Não foi possível ativar as abas clicáveis: ' + str(error))
            logging.exception('Falha nas abas clicáveis')
            return
    try:
        manager.sync()
    except Exception as error:
        manager.close()
        owner._click_tabs_active = False
        owner._click_tabs_failed = True
        owner.bar_cache = None
        owner.status.set('As abas clicáveis foram desativadas: ' + str(error))
        logging.exception('Falha ao posicionar as abas clicáveis')
