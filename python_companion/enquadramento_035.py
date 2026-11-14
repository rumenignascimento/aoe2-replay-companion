"""Enquadramento calibrado do losango do overlay sobre o minimapa nativo."""
import base64
import io
import math
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageChops
KEY = (255, 0, 255)
DEFAULTS = {'fit_minimap': False, 'fit_left': 0.7, 'fit_top': 0.7, 'fit_width': 0.25, 'fit_height': 0.25}

def rect(values, width, height):
    left = round(values['fit_left'] * width)
    top = round(values['fit_top'] * height)
    w = max(1, round(values['fit_width'] * width))
    h = max(1, round(values['fit_height'] * height))
    return (left, top, min(w, width - left), min(h, height - top))

def imagem_enquadrada(raw, width, height):
    image = Image.open(io.BytesIO(raw)).convert('RGB')
    w, h = image.size
    image = image.crop((round(w / 30), round(h / 30), round(w * 29 / 30), round(h * 29 / 30)))
    diff = ImageChops.difference(image, Image.new('RGB', image.size, KEY))
    channels = diff.split()
    mask = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2]).point(lambda x: 255 if x else 0)
    image.putalpha(mask)
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    mask = image.getchannel('A').point(lambda x: 255 if x >= 128 else 0)
    image = Image.composite(image.convert('RGB'), Image.new('RGB', image.size, KEY), mask)
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()

def ativar(g):
    if g.get('_enquadramento_035'):
        return
    g['_enquadramento_035'] = True
    p = g['p']
    p.CONFIG_DEFAULTS.update(DEFAULTS)
    old_validate = p._validate_config

    def validate(values):
        result = old_validate(values)
        for name in ('fit_left', 'fit_top', 'fit_width', 'fit_height'):
            value = result[name]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or (not math.isfinite(value)):
                raise ValueError('Área do minimapa inválida: ' + name)
            if not 0 <= value <= 1:
                raise ValueError('Área do minimapa fora da janela.')
        if result['fit_width'] <= 0 or result['fit_height'] <= 0 or result['fit_left'] + result['fit_width'] > 1.000001 or (result['fit_top'] + result['fit_height'] > 1.000001):
            raise ValueError('O enquadramento deve caber dentro da janela do jogo.')
        return result
    p._validate_config = validate
    Base = g['Window']

    class Queue:

        def __init__(self, inner, window):
            self.inner, self.window = (inner, window)

        def __getattr__(self, key):
            return getattr(self.inner, key)

        def get_nowait(self):
            result = self.inner.get_nowait()
            epoch, kind, session, data = result
            if epoch == self.window.epoch and kind == 'ok':
                self.window._fit_source = data.get('central_png', data['png'])
                self.window._fit_normal = data['png']
                self.window._fit_photo_key = None
                self.window._fit_display_fitted = False
            return result

    class Window(Base):

        def __init__(self, root, native):
            self.fit_minimap = tk.BooleanVar(master=root, value=False)
            for name, value in DEFAULTS.items():
                if name != 'fit_minimap':
                    setattr(self, name, tk.DoubleVar(master=root, value=value))
            self._fit_display_fitted = False
            self._fit_source = None
            self._fit_normal = None
            self._fit_photo_key = None
            self._fit_calibrating = False
            super().__init__(root, native)
            self.queue = Queue(self.queue, self)
            self.fit_minimap.trace_add('write', lambda *a: self.refresh_fit())

        def refresh_fit(self):
            self._fit_photo_key = None
            self.next_frame = 0

        def setup_minimap_fit_controls(self, parent):
            box = ttk.LabelFrame(parent, text='Enquadrar no minimapa do jogo', padding=8)
            box.pack(fill='x', pady=8)
            ttk.Checkbutton(box, text='Usar área calibrada', variable=self.fit_minimap).pack(anchor='w')
            ttk.Button(box, text='Calibrar área do minimapa · 5s', command=self.calibrar_minimapa).pack(fill='x', pady=6)
            ttk.Label(box, text='Clique em Calibrar e volte ao jogo em até 5 segundos.\nSelecione os limites do losango, sem a moldura e os botões.\nEsc cancela. Com o encaixe ativo, a área calibrada substitui largura e margens manuais.', wraplength=225).pack(anchor='w')

        def prepare_fit_photo(self, width=None, height=None):
            if width is None or height is None:
                area = self.native.game()
                if not area:
                    area = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
                width, height = (area[2], area[3])
            if self._fit_source is None:
                return
            if self.fit_minimap.get():
                values = {name: getattr(self, name).get() for name in DEFAULTS}
                left, top, w, h = rect(values, width, height)
                key = (id(self._fit_source), w, h, True)
                if self._fit_photo_key != key:
                    raw = imagem_enquadrada(self._fit_source, w, h)
                    self.photo = tk.PhotoImage(master=self.root, data=base64.b64encode(raw).decode())
                    self.image.configure(image=self.photo)
                    self._fit_photo_key = key
                    self._fit_display_fitted = True
            else:
                key = (id(self._fit_normal), False)
                if self._fit_display_fitted:
                    self.photo = tk.PhotoImage(master=self.root, data=base64.b64encode(self._fit_normal).decode())
                    self.image.configure(image=self.photo)
                self._fit_photo_key = key
                self._fit_display_fitted = False

        def overlay_position(self, x, y, width, height, iw, ih):
            if self.fit_minimap.get():
                values = {name: getattr(self, name).get() for name in DEFAULTS}
                left, top, w, h = rect(values, width, height)
                return (x + left, y + top)
            return super().overlay_position(x, y, width, height, iw, ih)

        def calibrar_minimapa(self):
            if self._fit_calibrating:
                return
            self._fit_calibrating = True
            old_show = self.show.get()
            old_caption = self.caption_show.get()
            self.show.set(False)
            self.caption_show.set(False)
            self.overlay.withdraw()
            self.caption.withdraw()
            self.root.withdraw()

            def finish():
                self._fit_calibrating = False
                self.show.set(old_show)
                self.caption_show.set(old_caption)
                self.root.deiconify()
                self.root.lift()

            def select():
                if self.closing:
                    return
                game = self.native.game()
                if not game:
                    finish()
                    self.status.set('Calibração cancelada: deixe o Age of Empires II DE em foco após clicar em Calibrar.')
                    return
                x, y, width, height = game
                popup = tk.Toplevel(self.root)
                popup.overrideredirect(True)
                popup.attributes('-topmost', True)
                popup.attributes('-alpha', 0.3)
                popup.geometry(f'{width}x{height}{x:+d}{y:+d}')
                canvas = tk.Canvas(popup, bg='black', highlightthickness=0, cursor='crosshair')
                canvas.pack(fill='both', expand=True)
                canvas.create_text(width // 2, 40, text='Arraste do canto superior esquerdo ao inferior direito dos limites do losango. Esc cancela.', fill='white', font=('Segoe UI', 13, 'bold'))
                start = []
                marker = [None]

                def close():
                    popup.destroy()
                    finish()

                def press(event):
                    start[:] = [max(0, min(width, event.x)), max(0, min(height, event.y))]

                def bounds(event):
                    return sorted((start[0], max(0, min(width, event.x)))) + sorted((start[1], max(0, min(height, event.y))))

                def drag(event):
                    if not start:
                        return
                    l, r, t, b = bounds(event)
                    if marker[0] is not None:
                        canvas.delete(marker[0])
                    marker[0] = canvas.create_rectangle(l, t, r, b, outline='#ffcf71', width=4)

                def release(event):
                    if not start:
                        return
                    l, r, t, b = bounds(event)
                    if r - l < 100 or b - t < 50:
                        self.status.set('Área muito pequena. Selecione todo o losango do minimapa.')
                        return
                    self.fit_left.set(l / width)
                    self.fit_top.set(t / height)
                    self.fit_width.set((r - l) / width)
                    self.fit_height.set((b - t) / height)
                    self.fit_minimap.set(True)
                    close()
                    self.show.set(True)
                    self.refresh_fit()
                    self.save_settings()
                canvas.bind('<ButtonPress-1>', press)
                canvas.bind('<B1-Motion>', drag)
                canvas.bind('<ButtonRelease-1>', release)
                popup.bind('<Escape>', lambda event: close())
                popup.update_idletasks()
                hwnd = self.native.u.GetAncestor(popup.winfo_id(), 2)
                self.native.u.SetWindowPos(hwnd, None, x, y, width, height, 20)
                popup.focus_force()
            self.root.after(5000, select)
    g['Window'] = Window
