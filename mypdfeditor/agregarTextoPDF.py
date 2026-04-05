from __future__ import annotations

import io
from dataclasses import dataclass
from itertools import count
from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog, font as tkfont, messagebox, ttk

import fitz
from PIL import Image, ImageDraw, ImageFont, ImageTk


PREVIEW_ZOOM = 1.25
EXPORT_ZOOM = 2.0
MIN_FONT_SIZE = 8


@dataclass
class TextOverlay:
    overlay_id: int
    page_index: int
    overlay_type: str
    text: str
    x: float
    y: float
    font_family: str
    font_size: int
    color: str
    rotation: float
    align: str
    signature_png: bytes | None = None
    signature_width: float = 0.0
    signature_height: float = 0.0


class SignaturePad(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_save) -> None:
        super().__init__(master)
        self.title("Dibujar firma")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.on_save = on_save
        self.canvas_width = 520
        self.canvas_height = 180
        self.last_point: tuple[int, int] | None = None
        self.signature_image = Image.new("RGBA", (self.canvas_width, self.canvas_height), (0, 0, 0, 0))
        self.signature_draw = ImageDraw.Draw(self.signature_image)

        container = ttk.Frame(self, padding=14)
        container.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            container,
            text="Dibuja la firma con el raton. Luego pulsa Usar firma.",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        self.signature_canvas = tk.Canvas(
            container,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="white",
            relief="solid",
            borderwidth=1,
            cursor="pencil",
        )
        self.signature_canvas.grid(row=1, column=0, columnspan=3, sticky="nsew")
        self.signature_canvas.bind("<Button-1>", self.start_stroke)
        self.signature_canvas.bind("<B1-Motion>", self.draw_stroke)
        self.signature_canvas.bind("<ButtonRelease-1>", self.finish_stroke)

        ttk.Button(container, text="Limpiar", command=self.clear_signature).grid(
            row=2, column=0, sticky="ew", pady=(12, 0), padx=(0, 6)
        )
        ttk.Button(container, text="Cancelar", command=self.destroy).grid(
            row=2, column=1, sticky="ew", pady=(12, 0), padx=6
        )
        ttk.Button(container, text="Usar firma", command=self.save_signature).grid(
            row=2, column=2, sticky="ew", pady=(12, 0), padx=(6, 0)
        )

    def start_stroke(self, event: tk.Event[tk.Misc]) -> None:
        self.last_point = (event.x, event.y)
        radius = 2
        self.signature_canvas.create_oval(
            event.x - radius,
            event.y - radius,
            event.x + radius,
            event.y + radius,
            fill="#111111",
            outline="#111111",
        )
        self.signature_draw.ellipse(
            (event.x - radius, event.y - radius, event.x + radius, event.y + radius),
            fill="#111111",
            outline="#111111",
        )

    def draw_stroke(self, event: tk.Event[tk.Misc]) -> None:
        if self.last_point is None:
            self.last_point = (event.x, event.y)
            return

        x0, y0 = self.last_point
        x1, y1 = event.x, event.y
        self.signature_canvas.create_line(
            x0,
            y0,
            x1,
            y1,
            fill="#111111",
            width=4,
            smooth=True,
            capstyle=tk.ROUND,
        )
        self.signature_draw.line((x0, y0, x1, y1), fill="#111111", width=4)
        self.last_point = (x1, y1)

    def finish_stroke(self, _event: tk.Event[tk.Misc]) -> None:
        self.last_point = None

    def clear_signature(self) -> None:
        self.signature_canvas.delete("all")
        self.signature_image = Image.new("RGBA", (self.canvas_width, self.canvas_height), (0, 0, 0, 0))
        self.signature_draw = ImageDraw.Draw(self.signature_image)
        self.last_point = None

    def save_signature(self) -> None:
        bbox = self.signature_image.getbbox()
        if bbox is None:
            messagebox.showwarning("Firma vacia", "Dibuja una firma antes de guardarla.", parent=self)
            return

        padding = 8
        left = max(bbox[0] - padding, 0)
        top = max(bbox[1] - padding, 0)
        right = min(bbox[2] + padding, self.canvas_width)
        bottom = min(bbox[3] + padding, self.canvas_height)
        cropped = self.signature_image.crop((left, top, right, bottom))

        buffer = io.BytesIO()
        cropped.save(buffer, format="PNG")
        self.on_save(buffer.getvalue(), cropped.width, cropped.height)
        self.destroy()


class PDFTextEditor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("My PDF Editor")
        self.geometry("1380x900")
        self.minsize(1100, 720)

        self.doc: fitz.Document | None = None
        self.pdf_path: Path | None = None
        self.current_page_index = 0
        self.preview_cache: dict[int, Image.Image] = {}
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.canvas_overlay_items: dict[int, int] = {}
        self.canvas_overlay_refs: dict[int, ImageTk.PhotoImage] = {}
        self.canvas_selection_box: int | None = None
        self.overlays_by_page: dict[int, list[TextOverlay]] = {}
        self.overlay_counter = count(1)
        self.selected_overlay_id: int | None = None
        self.pending_signature: tuple[bytes, float, float] | None = None
        self.drag_overlay_id: int | None = None
        self.drag_offset_x = 0.0
        self.drag_offset_y = 0.0
        self.font_path_cache: dict[str, str | None] = {}
        self.pil_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
        self.status_var = tk.StringVar(value="Abre un PDF para empezar.")
        self.page_var = tk.IntVar(value=1)
        self.font_size_var = tk.IntVar(value=28)
        self.rotation_var = tk.DoubleVar(value=0.0)
        self.font_family_var = tk.StringVar(value="Arial")
        self.align_var = tk.StringVar(value="left")
        self.color_var = tk.StringVar(value="#111111")

        self._build_ui()
        self.bind_all("<Delete>", self.on_delete_key)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, padding=16)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_columnconfigure(0, weight=1)

        viewer = ttk.Frame(self, padding=(0, 16, 16, 16))
        viewer.grid(row=0, column=1, sticky="nsew")
        viewer.grid_columnconfigure(0, weight=1)
        viewer.grid_rowconfigure(1, weight=1)

        ttk.Label(sidebar, text="My PDF Editor", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            sidebar,
            text="Abre un PDF, haz clic en la pagina y coloca texto visualmente.",
            wraplength=260,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 16))

        ttk.Button(sidebar, text="Abrir PDF", command=self.open_pdf).grid(
            row=2, column=0, sticky="ew"
        )
        ttk.Button(sidebar, text="Dibujar firma", command=self.open_signature_pad).grid(
            row=3, column=0, sticky="ew", pady=(8, 0)
        )
        ttk.Button(sidebar, text="Exportar PDF", command=self.export_pdf).grid(
            row=4, column=0, sticky="ew", pady=(8, 0)
        )

        nav_frame = ttk.LabelFrame(sidebar, text="Paginas", padding=10)
        nav_frame.grid(row=5, column=0, sticky="ew", pady=(18, 0))
        nav_frame.grid_columnconfigure(1, weight=1)

        ttk.Button(nav_frame, text="<", width=3, command=self.previous_page).grid(
            row=0, column=0, padx=(0, 6)
        )
        self.page_spinbox = ttk.Spinbox(
            nav_frame,
            from_=1,
            to=1,
            textvariable=self.page_var,
            width=8,
            command=self.go_to_page_from_spinbox,
        )
        self.page_spinbox.grid(row=0, column=1, sticky="ew")
        ttk.Button(nav_frame, text=">", width=3, command=self.next_page).grid(
            row=0, column=2, padx=(6, 0)
        )
        self.page_spinbox.bind("<Return>", lambda _event: self.go_to_page_from_spinbox())
        self.page_info_label = ttk.Label(nav_frame, text="Pagina 0 de 0")
        self.page_info_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        properties = ttk.LabelFrame(sidebar, text="Texto", padding=10)
        properties.grid(row=6, column=0, sticky="nsew", pady=(18, 0))
        properties.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(6, weight=1)

        ttk.Label(properties, text="Contenido").grid(row=0, column=0, sticky="w")
        self.text_input = tk.Text(properties, height=5, width=28, wrap="word")
        self.text_input.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        self.text_input.insert("1.0", "Escribe aqui")

        available_fonts = sorted(set(tkfont.families()))
        if available_fonts and self.font_family_var.get() not in available_fonts:
            self.font_family_var.set(available_fonts[0])

        ttk.Label(properties, text="Fuente").grid(row=2, column=0, sticky="w")
        self.font_family_combo = ttk.Combobox(
            properties,
            textvariable=self.font_family_var,
            values=available_fonts,
            state="readonly",
        )
        self.font_family_combo.grid(row=3, column=0, sticky="ew", pady=(4, 10))

        ttk.Label(properties, text="Tamano").grid(row=4, column=0, sticky="w")
        ttk.Spinbox(
            properties,
            from_=MIN_FONT_SIZE,
            to=240,
            textvariable=self.font_size_var,
            width=10,
        ).grid(row=5, column=0, sticky="w", pady=(4, 10))

        ttk.Label(properties, text="Rotacion").grid(row=6, column=0, sticky="w")
        ttk.Spinbox(
            properties,
            from_=-360,
            to=360,
            increment=5,
            textvariable=self.rotation_var,
            width=10,
        ).grid(row=7, column=0, sticky="w", pady=(4, 10))

        ttk.Label(properties, text="Alineacion").grid(row=8, column=0, sticky="w")
        ttk.Combobox(
            properties,
            textvariable=self.align_var,
            values=("left", "center", "right"),
            state="readonly",
        ).grid(row=9, column=0, sticky="ew", pady=(4, 10))

        color_row = ttk.Frame(properties)
        color_row.grid(row=10, column=0, sticky="ew")
        color_row.grid_columnconfigure(1, weight=1)
        ttk.Label(color_row, text="Color").grid(row=0, column=0, sticky="w")
        self.color_preview = tk.Label(color_row, bg=self.color_var.get(), width=3, relief="solid")
        self.color_preview.grid(row=0, column=1, sticky="e", padx=(8, 0))
        ttk.Button(properties, text="Elegir color", command=self.choose_color).grid(
            row=11, column=0, sticky="ew", pady=(4, 14)
        )

        ttk.Button(properties, text="Aplicar al texto seleccionado", command=self.apply_form_to_selected).grid(
            row=12, column=0, sticky="ew"
        )
        ttk.Button(properties, text="Eliminar texto seleccionado", command=self.delete_selected_overlay).grid(
            row=13, column=0, sticky="ew", pady=(8, 0)
        )

        tips = ttk.LabelFrame(sidebar, text="Uso rapido", padding=10)
        tips.grid(row=7, column=0, sticky="ew", pady=(18, 0))
        ttk.Label(
            tips,
            text=(
                "1. Abre un PDF.\n"
                "2. Cambia texto y estilo o dibuja una firma.\n"
                "3. Haz clic sobre la pagina para insertar.\n"
                "4. Arrastra para recolocar.\n"
                "5. Usa Supr para borrar.\n"
                "6. Exporta el PDF final."
            ),
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        toolbar = ttk.Frame(viewer)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)
        self.file_label = ttk.Label(toolbar, text="Ningun archivo cargado")
        self.file_label.grid(row=0, column=0, sticky="w")

        canvas_frame = ttk.Frame(viewer)
        canvas_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="#c9ced6", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        self.canvas.bind("<Button-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        status = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w")
        status.grid(row=1, column=0, columnspan=2, sticky="ew")

    def open_pdf(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecciona un PDF",
            filetypes=[("PDF", "*.pdf")],
        )
        if not file_path:
            return

        try:
            self.load_pdf(Path(file_path))
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir el PDF.\n\n{exc}")

    def load_pdf(self, pdf_path: Path) -> None:
        if self.doc is not None:
            self.doc.close()

        self.doc = fitz.open(pdf_path)
        self.pdf_path = pdf_path
        self.current_page_index = 0
        self.preview_cache.clear()
        self.overlays_by_page.clear()
        self.selected_overlay_id = None
        self.pending_signature = None
        self.drag_overlay_id = None
        self.canvas_overlay_items.clear()
        self.canvas_overlay_refs.clear()
        self.file_label.configure(text=str(pdf_path))
        self.page_spinbox.configure(to=max(len(self.doc), 1))
        self.page_var.set(1)
        self.status_var.set("PDF cargado. Haz clic en la pagina para insertar texto.")
        self.render_current_page()

    def render_current_page(self) -> None:
        if self.doc is None:
            return

        page = self.doc.load_page(self.current_page_index)
        page_image = self.get_preview_page_image(self.current_page_index)
        self.preview_photo = ImageTk.PhotoImage(page_image)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.preview_photo, anchor="nw", tags=("page",))
        self.canvas.configure(scrollregion=(0, 0, page_image.width, page_image.height))

        self.canvas_overlay_items.clear()
        self.canvas_overlay_refs.clear()
        self.canvas_selection_box = None

        for overlay in self.overlays_by_page.get(self.current_page_index, []):
            overlay_image, offset_x, offset_y = self.build_overlay_image(overlay, PREVIEW_ZOOM)
            photo = ImageTk.PhotoImage(overlay_image)
            canvas_x = overlay.x * PREVIEW_ZOOM + offset_x
            canvas_y = overlay.y * PREVIEW_ZOOM + offset_y
            item_id = self.canvas.create_image(
                canvas_x,
                canvas_y,
                image=photo,
                anchor="nw",
                tags=("overlay", f"overlay:{overlay.overlay_id}"),
            )
            self.canvas_overlay_items[overlay.overlay_id] = item_id
            self.canvas_overlay_refs[overlay.overlay_id] = photo

        self.draw_selection_box()
        self.page_info_label.configure(
            text=f"Pagina {self.current_page_index + 1} de {len(self.doc)} | {int(page.rect.width)} x {int(page.rect.height)} pt"
        )
        self.page_var.set(self.current_page_index + 1)

    def get_preview_page_image(self, page_index: int) -> Image.Image:
        if page_index not in self.preview_cache:
            self.preview_cache[page_index] = self.render_page_image(page_index, PREVIEW_ZOOM)
        return self.preview_cache[page_index]

    def render_page_image(self, page_index: int, zoom: float) -> Image.Image:
        if self.doc is None:
            raise RuntimeError("No hay PDF cargado.")

        page = self.doc.load_page(page_index)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

    def on_canvas_press(self, event: tk.Event[tk.Misc]) -> None:
        if self.doc is None:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        current_items = self.canvas.find_withtag("current")

        if current_items:
            current_item = current_items[0]
            tags = self.canvas.gettags(current_item)
            overlay_tag = next((tag for tag in tags if tag.startswith("overlay:")), None)
            if overlay_tag is not None:
                overlay_id = int(overlay_tag.split(":", maxsplit=1)[1])
                overlay = self.get_overlay_by_id(overlay_id)
                if overlay is None:
                    return

                self.select_overlay(overlay_id)
                self.drag_overlay_id = overlay_id
                self.drag_offset_x = overlay.x - (canvas_x / PREVIEW_ZOOM)
                self.drag_offset_y = overlay.y - (canvas_y / PREVIEW_ZOOM)
                self.status_var.set("Arrastrando texto seleccionado.")
                return

        if self.pending_signature is not None:
            self.create_signature_overlay_from_pending(canvas_x / PREVIEW_ZOOM, canvas_y / PREVIEW_ZOOM)
            return

        self.create_overlay_from_form(canvas_x / PREVIEW_ZOOM, canvas_y / PREVIEW_ZOOM)

    def on_canvas_drag(self, event: tk.Event[tk.Misc]) -> None:
        if self.drag_overlay_id is None or self.doc is None:
            return

        overlay = self.get_overlay_by_id(self.drag_overlay_id)
        if overlay is None:
            return

        page = self.doc.load_page(overlay.page_index)
        new_x = self.canvas.canvasx(event.x) / PREVIEW_ZOOM + self.drag_offset_x
        new_y = self.canvas.canvasy(event.y) / PREVIEW_ZOOM + self.drag_offset_y
        overlay.x = min(max(new_x, 0), page.rect.width)
        overlay.y = min(max(new_y, 0), page.rect.height)
        self.render_current_page()

    def on_canvas_release(self, _event: tk.Event[tk.Misc]) -> None:
        if self.drag_overlay_id is not None:
            self.status_var.set("Posicion actualizada.")
        self.drag_overlay_id = None

    def create_overlay_from_form(self, x: float, y: float) -> None:
        if self.doc is None:
            return

        text = self.get_form_text()
        if not text:
            messagebox.showwarning("Texto vacio", "Escribe un texto antes de insertar.")
            return

        overlay = TextOverlay(
            overlay_id=next(self.overlay_counter),
            page_index=self.current_page_index,
            overlay_type="text",
            text=text,
            x=x,
            y=y,
            font_family=self.font_family_var.get(),
            font_size=max(self.font_size_var.get(), MIN_FONT_SIZE),
            color=self.color_var.get(),
            rotation=self.rotation_var.get(),
            align=self.align_var.get(),
        )
        self.overlays_by_page.setdefault(self.current_page_index, []).append(overlay)
        self.select_overlay(overlay.overlay_id)
        self.status_var.set("Texto insertado. Puedes arrastrarlo para recolocarlo.")
        self.render_current_page()

    def create_signature_overlay_from_pending(self, x: float, y: float) -> None:
        if self.doc is None or self.pending_signature is None:
            return

        signature_png, signature_width, signature_height = self.pending_signature
        overlay = TextOverlay(
            overlay_id=next(self.overlay_counter),
            page_index=self.current_page_index,
            overlay_type="signature",
            text="",
            x=x,
            y=y,
            font_family=self.font_family_var.get(),
            font_size=max(self.font_size_var.get(), MIN_FONT_SIZE),
            color="#111111",
            rotation=self.rotation_var.get(),
            align="left",
            signature_png=signature_png,
            signature_width=signature_width,
            signature_height=signature_height,
        )
        self.overlays_by_page.setdefault(self.current_page_index, []).append(overlay)
        self.pending_signature = None
        self.select_overlay(overlay.overlay_id)
        self.status_var.set("Firma insertada. Puedes moverla o borrarla con Supr.")
        self.render_current_page()

    def apply_form_to_selected(self) -> None:
        overlay = self.get_overlay_by_id(self.selected_overlay_id)
        if overlay is None:
            messagebox.showinfo("Sin seleccion", "Selecciona un texto para modificarlo.")
            return

        if overlay.overlay_type == "signature":
            overlay.rotation = self.rotation_var.get()
            self.status_var.set("Rotacion aplicada a la firma seleccionada.")
            self.render_current_page()
            return

        text = self.get_form_text()
        if not text:
            messagebox.showwarning("Texto vacio", "El contenido no puede quedar vacio.")
            return

        overlay.text = text
        overlay.font_family = self.font_family_var.get()
        overlay.font_size = max(self.font_size_var.get(), MIN_FONT_SIZE)
        overlay.color = self.color_var.get()
        overlay.rotation = self.rotation_var.get()
        overlay.align = self.align_var.get()
        self.status_var.set("Cambios aplicados al texto seleccionado.")
        self.render_current_page()

    def delete_selected_overlay(self) -> None:
        if self.selected_overlay_id is None:
            return

        overlays = self.overlays_by_page.get(self.current_page_index, [])
        self.overlays_by_page[self.current_page_index] = [
            overlay for overlay in overlays if overlay.overlay_id != self.selected_overlay_id
        ]
        self.selected_overlay_id = None
        self.status_var.set("Texto eliminado.")
        self.render_current_page()

    def on_delete_key(self, event: tk.Event[tk.Misc]) -> str | None:
        focused_widget = self.focus_get()
        if isinstance(focused_widget, (tk.Text, tk.Entry, ttk.Entry, ttk.Spinbox, ttk.Combobox)):
            return None

        if self.selected_overlay_id is None:
            return None

        self.delete_selected_overlay()
        return "break"

    def previous_page(self) -> None:
        if self.doc is None or self.current_page_index == 0:
            return

        self.current_page_index -= 1
        self.status_var.set("Pagina anterior.")
        self.render_current_page()

    def next_page(self) -> None:
        if self.doc is None or self.current_page_index >= len(self.doc) - 1:
            return

        self.current_page_index += 1
        self.status_var.set("Pagina siguiente.")
        self.render_current_page()

    def go_to_page_from_spinbox(self) -> None:
        if self.doc is None:
            return

        try:
            page_number = int(self.page_var.get())
        except (tk.TclError, ValueError):
            return

        page_number = min(max(page_number, 1), len(self.doc))
        self.current_page_index = page_number - 1
        self.render_current_page()

    def choose_color(self) -> None:
        color = colorchooser.askcolor(initialcolor=self.color_var.get(), title="Selecciona un color")
        if color[1] is None:
            return

        self.color_var.set(color[1])
        self.color_preview.configure(bg=color[1])

    def select_overlay(self, overlay_id: int) -> None:
        overlay = self.get_overlay_by_id(overlay_id)
        if overlay is None:
            return

        self.selected_overlay_id = overlay_id
        self.rotation_var.set(overlay.rotation)

        if overlay.overlay_type == "signature":
            self.status_var.set("Firma seleccionada. Puedes moverla, girarla o eliminarla con Supr.")
            return

        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", overlay.text)
        self.font_family_var.set(overlay.font_family)
        self.font_size_var.set(overlay.font_size)
        self.align_var.set(overlay.align)
        self.color_var.set(overlay.color)
        self.color_preview.configure(bg=overlay.color)

    def draw_selection_box(self) -> None:
        if self.selected_overlay_id is None:
            return

        item_id = self.canvas_overlay_items.get(self.selected_overlay_id)
        if item_id is None:
            return

        bbox = self.canvas.bbox(item_id)
        if bbox is None:
            return

        self.canvas_selection_box = self.canvas.create_rectangle(
            bbox[0] - 4,
            bbox[1] - 4,
            bbox[2] + 4,
            bbox[3] + 4,
            outline="#1177cc",
            width=2,
            dash=(5, 3),
        )

    def get_form_text(self) -> str:
        return self.text_input.get("1.0", "end").strip()

    def get_overlay_by_id(self, overlay_id: int | None) -> TextOverlay | None:
        if overlay_id is None:
            return None

        for overlays in self.overlays_by_page.values():
            for overlay in overlays:
                if overlay.overlay_id == overlay_id:
                    return overlay
        return None

    def build_overlay_image(self, overlay: TextOverlay, zoom: float) -> tuple[Image.Image, float, float]:
        if overlay.overlay_type == "signature":
            image = Image.open(io.BytesIO(overlay.signature_png or b""))
            image = image.convert("RGBA")
            target_width = max(int(overlay.signature_width * zoom), 1)
            target_height = max(int(overlay.signature_height * zoom), 1)
            if image.size != (target_width, target_height):
                image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            if overlay.rotation:
                image = image.rotate(-overlay.rotation, expand=True, resample=Image.Resampling.BICUBIC)
            return image, 0.0, 0.0

        font_size_px = max(int(overlay.font_size * zoom), MIN_FONT_SIZE)
        font = self.get_pil_font(overlay.font_family, font_size_px)
        spacing = max(font_size_px // 5, 4)
        dummy = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.multiline_textbbox(
            (0, 0),
            overlay.text,
            font=font,
            align=overlay.align,
            spacing=spacing,
        )

        padding = max(font_size_px // 3, 8)
        text_width = max(bbox[2] - bbox[0], 1)
        text_height = max(bbox[3] - bbox[1], 1)
        image = Image.new(
            "RGBA",
            (text_width + padding * 2, text_height + padding * 2),
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(image)
        draw.multiline_text(
            (padding - bbox[0], padding - bbox[1]),
            overlay.text,
            font=font,
            fill=overlay.color,
            align=overlay.align,
            spacing=spacing,
        )

        if overlay.rotation:
            image = image.rotate(-overlay.rotation, expand=True, resample=Image.Resampling.BICUBIC)

        if overlay.align == "center":
            offset_x = -image.width / 2
        elif overlay.align == "right":
            offset_x = -image.width
        else:
            offset_x = 0.0

        return image, offset_x, 0.0

    def get_pil_font(self, family_name: str, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        cache_key = (family_name, font_size)
        if cache_key in self.pil_font_cache:
            return self.pil_font_cache[cache_key]

        candidates = []
        font_path = self.find_font_path(family_name)
        if font_path:
            candidates.append(font_path)
        candidates.extend([family_name, "arial.ttf", "calibri.ttf", "segoeui.ttf", "DejaVuSans.ttf"])

        for candidate in candidates:
            try:
                font = ImageFont.truetype(candidate, font_size)
                self.pil_font_cache[cache_key] = font
                return font
            except OSError:
                continue

        font = ImageFont.load_default()
        self.pil_font_cache[cache_key] = font
        return font

    def find_font_path(self, family_name: str) -> str | None:
        normalized_name = self.normalize_font_name(family_name)
        if normalized_name in self.font_path_cache:
            return self.font_path_cache[normalized_name]

        fonts_dir = Path("C:/Windows/Fonts")
        if not fonts_dir.exists():
            self.font_path_cache[normalized_name] = None
            return None

        best_match = None
        for file_path in fonts_dir.iterdir():
            if file_path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
                continue

            stem_normalized = self.normalize_font_name(file_path.stem)
            if stem_normalized == normalized_name:
                best_match = str(file_path)
                break
            if normalized_name and normalized_name in stem_normalized and best_match is None:
                best_match = str(file_path)

        self.font_path_cache[normalized_name] = best_match
        return best_match

    @staticmethod
    def normalize_font_name(font_name: str) -> str:
        return "".join(char for char in font_name.lower() if char.isalnum())

    def export_pdf(self) -> None:
        if self.doc is None or self.pdf_path is None:
            messagebox.showinfo("Sin PDF", "Abre un PDF antes de exportar.")
            return

        default_name = self.pdf_path.with_name(f"{self.pdf_path.stem}_con_texto.pdf")
        save_path = filedialog.asksaveasfilename(
            title="Guardar PDF final",
            defaultextension=".pdf",
            initialfile=default_name.name,
            filetypes=[("PDF", "*.pdf")],
        )
        if not save_path:
            return

        output_doc = fitz.open()
        try:
            for page_index in range(len(self.doc)):
                source_page = self.doc.load_page(page_index)
                base_image = self.render_page_image(page_index, EXPORT_ZOOM).convert("RGBA")

                for overlay in self.overlays_by_page.get(page_index, []):
                    overlay_image, offset_x, offset_y = self.build_overlay_image(overlay, EXPORT_ZOOM)
                    paste_x = int(overlay.x * EXPORT_ZOOM + offset_x)
                    paste_y = int(overlay.y * EXPORT_ZOOM + offset_y)
                    base_image.alpha_composite(overlay_image, (paste_x, paste_y))

                rgb_image = base_image.convert("RGB")
                stream = io.BytesIO()
                rgb_image.save(stream, format="PNG")
                stream.seek(0)

                output_page = output_doc.new_page(
                    width=source_page.rect.width,
                    height=source_page.rect.height,
                )
                output_page.insert_image(source_page.rect, stream=stream.getvalue())

            output_doc.save(save_path, deflate=True, garbage=4, clean=True)
            self.status_var.set(f"PDF exportado correctamente: {save_path}")
            messagebox.showinfo("Exportacion completa", f"PDF guardado en:\n{save_path}")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo exportar el PDF.\n\n{exc}")
        finally:
            output_doc.close()

    def open_signature_pad(self) -> None:
        if self.doc is None:
            messagebox.showinfo("Sin PDF", "Abre un PDF antes de dibujar una firma.")
            return

        SignaturePad(self, self.store_pending_signature)

    def store_pending_signature(self, signature_png: bytes, source_width: int, source_height: int) -> None:
        base_width = min(max(source_width * 0.45, 90), 260)
        scale = base_width / max(source_width, 1)
        base_height = max(source_height * scale, 28)
        self.pending_signature = (signature_png, base_width, base_height)
        self.status_var.set("Firma lista. Haz clic sobre la pagina para colocarla.")

    def destroy(self) -> None:
        if self.doc is not None:
            self.doc.close()
            self.doc = None
        super().destroy()


def main() -> None:
    app = PDFTextEditor()
    app.mainloop()


if __name__ == "__main__":
    main()