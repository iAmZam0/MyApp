import os
import json
from decimal import Decimal, InvalidOperation
from datetime import date

from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Colores de la interfaz
BG = (255, 255, 255)
PANEL = (255, 255, 255)
PANEL_2 = (255, 255, 255)
WHITE = (0.95, 0.96, 0.98, 1)
MUTED = (0.68, 0.71, 0.77, 1)
GREEN = (0.20, 0.65, 0.42, 1)
BLUE = (255, 255, 255)
RED = (0.76, 0.25, 0.27, 1)


def money(value):
    return f"${Decimal(value):,.2f}"


class SacarCuentasApp(App):
    def build(self):
        self.title = "Sacar Cuentas"
        Window.clearcolor = BG

        self.clientes = []
        self.cliente_editando = None
        self.precios_temporales = []

        self.cargar_datos()

        root = BoxLayout(
            orientation="vertical",
            padding=[dp(14), dp(12), dp(14), dp(12)],
            spacing=dp(10)
        )

        header = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(76),
            spacing=dp(4)
        )
        header.add_widget(Label(
            text="[b]SACAR CUENTAS[/b]",
            markup=True,
            color="#000000",
            font_size="23sp",
            halign="left",
            valign="middle"
        ))
        root.add_widget(header)

        actions = GridLayout(
            cols=2,
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8)
        )
        actions.add_widget(self.make_button("Añadir cliente", WHITE, self.abrir_nuevo))
        actions.add_widget(self.make_button("Generar PDF", WHITE, self.generar_pdf))
        root.add_widget(actions)

        self.lista_scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self.lista_clientes = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=[0, dp(3), 0, dp(8)],
            size_hint_y=None
        )
        self.lista_clientes.bind(minimum_height=self.lista_clientes.setter("height"))
        self.lista_scroll.add_widget(self.lista_clientes)
        root.add_widget(self.lista_scroll)

        self.total_general_label = Label(
            text="Total general: $0.00",
            color="#000000",
            bold=True,
            font_size="18sp",
            size_hint_y=None,
            height=dp(42),
            halign="right",
            valign="middle"
        )
        root.add_widget(self.total_general_label)

        self.actualizar_lista()
        return root

    def make_button(self, text, color, callback, height=46):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=dp(height),
            background_normal="",
            background_down="",
            background_color=color,
            color="#000000",
            font_size="14sp",
            bold=True
        )
        btn.bind(on_release=callback)
        return btn

    def mostrar_mensaje(self, titulo, mensaje):
        contenido = BoxLayout(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(12)
        )
        contenido.add_widget(Label(
            text=str(mensaje),
            color=WHITE,
            halign="center",
            valign="middle"
        ))
        popup = Popup(
            title=titulo,
            content=contenido,
            size_hint=(0.88, None),
            height=dp(210),
            separator_color=BLUE
        )
        contenido.add_widget(self.make_button("Aceptar", BLUE, popup.dismiss, 42))
        popup.open()

    def cargar_datos(self):
        ruta = os.path.join(self.user_data_dir, "clientes.json")
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            self.clientes = [
                {
                    "nombre": str(item.get("nombre", "")),
                    "precios": [str(Decimal(p)) for p in item.get("precios", [])]
                }
                for item in datos
            ]
        except (FileNotFoundError, json.JSONDecodeError, OSError, InvalidOperation, TypeError):
            self.clientes = []

    def guardar_datos_archivo(self):
        ruta = os.path.join(self.user_data_dir, "clientes.json")
        temporal = ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(self.clientes, archivo, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)

    def actualizar_lista(self):
        self.lista_clientes.clear_widgets()

        total_general = Decimal("0")

        for indice, cliente in enumerate(self.clientes):
            total = sum((Decimal(p) for p in cliente["precios"]), Decimal("0"))
            total_general += total

            tarjeta = BoxLayout(
                orientation="vertical",
                padding=dp(10),
                spacing=dp(7),
                size_hint_y=None,
                height=dp(112)
            )
            # Fondo de tarjeta mediante color de botones transparentes no requerido:
            # se usa un botón contenedor visual con fondo sólido.
            tarjeta_canvas = Button(
                text="",
                disabled=True,
                background_normal="",
                background_color=PANEL
            )
            tarjeta.add_widget(Label(
                text=f"[b]{cliente['nombre']}[/b]",
                markup=True,
                color="#000000",
                font_size="17sp",
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=dp(27)
            ))
            tarjeta.add_widget(Label(
                text=f"Total: {money(total)}   •   {len(cliente['precios'])} precio(s)",
                color="#000000",
                font_size="14sp",
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=dp(23)
            ))

            botones = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(7))
            botones.add_widget(self.make_button("Editar", WHITE, lambda _btn, i=indice: self.abrir_edicion(i), 36))
            botones.add_widget(self.make_button("Eliminar", RED, lambda _btn, i=indice: self.confirmar_eliminar(i), 36))
            tarjeta.add_widget(botones)

            # El contenedor usa un color de fondo dibujado en canvas.
            from kivy.graphics import Color, RoundedRectangle
            with tarjeta.canvas.before:
                Color(*PANEL)
                rect = RoundedRectangle(pos=tarjeta.pos, size=tarjeta.size, radius=[dp(10)])
            tarjeta.bind(pos=lambda widget, value, r=rect: setattr(r, "pos", value))
            tarjeta.bind(size=lambda widget, value, r=rect: setattr(r, "size", value))

            self.lista_clientes.add_widget(tarjeta)

        self.total_general_label.text = f"Total general: {money(total_general)}"

    def confirmar_eliminar(self, indice):
        cliente = self.clientes[indice]
        contenido = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))
        contenido.add_widget(Label(
            text=f"¿Eliminar a «{cliente['nombre']}»?",
            color=WHITE,
            halign="center"
        ))
        botones = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        popup = Popup(
            title="Confirmar eliminación",
            content=contenido,
            size_hint=(0.88, None),
            height=dp(180)
        )
        botones.add_widget(self.make_button("Cancelar", PANEL_2, popup.dismiss))
        botones.add_widget(self.make_button(
            "Eliminar", RED,
            lambda _btn: self.eliminar_cliente(indice, popup)
        ))
        contenido.add_widget(botones)
        popup.open()

    def eliminar_cliente(self, indice, popup):
        del self.clientes[indice]
        self.guardar_datos_archivo()
        self.actualizar_lista()
        popup.dismiss()

    def abrir_nuevo(self, *_):
        self.abrir_editor(None)

    def abrir_edicion(self, indice):
        self.abrir_editor(indice)

    def abrir_editor(self, indice):
        self.cliente_editando = indice
        if indice is None:
            nombre = ""
            self.precios_temporales = []
            titulo = "Añadir cliente"
        else:
            cliente = self.clientes[indice]
            nombre = cliente["nombre"]
            self.precios_temporales = list(cliente["precios"])
            titulo = "Editar cliente"

        contenido = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )

        contenido.add_widget(Label(
            text="Nombre del cliente",
            color=WHITE,
            size_hint_y=None,
            height=dp(24),
            halign="left"
        ))
        self.nombre_input = TextInput(
            text=nombre,
            hint_text="Escribe el nombre",
            multiline=False,
            size_hint_y=None,
            height=dp(46),
            font_size="17sp",
            padding=[dp(10), dp(10)]
        )
        contenido.add_widget(self.nombre_input)

        contenido.add_widget(Label(
            text="Agregar precio",
            color=WHITE,
            size_hint_y=None,
            height=dp(24),
            halign="left"
        ))

        fila_precio = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(7))
        self.precio_input = TextInput(
            hint_text="Ej. 150.50",
            multiline=False,
            input_filter="float",
            font_size="16sp",
            padding=[dp(10), dp(10)]
        )
        fila_precio.add_widget(self.precio_input)
        fila_precio.add_widget(self.make_button("Añadir", WHITE, self.agregar_precio, 46))
        contenido.add_widget(fila_precio)

        self.precios_scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1))
        self.precios_lista = GridLayout(
            cols=1,
            spacing=dp(5),
            size_hint_y=None
        )
        self.precios_lista.bind(minimum_height=self.precios_lista.setter("height"))
        self.precios_scroll.add_widget(self.precios_lista)
        contenido.add_widget(self.precios_scroll)

        self.total_editor_label = Label(
            text="Total: $0.00",
            color=WHITE,
            bold=True,
            font_size="17sp",
            size_hint_y=None,
            height=dp(34)
        )
        contenido.add_widget(self.total_editor_label)

        botones = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self.editor_popup = Popup(
            title=titulo,
            content=contenido,
            size_hint=(0.94, 0.88),
            auto_dismiss=False
        )
        botones.add_widget(self.make_button("Cancelar", PANEL_2, self.editor_popup.dismiss))
        botones.add_widget(self.make_button("Guardar", BLUE, self.guardar_cliente))
        contenido.add_widget(botones)

        self.actualizar_precios_editor()
        self.editor_popup.open()

    def agregar_precio(self, *_):
        texto = self.precio_input.text.strip().replace(",", ".")
        if not texto:
            self.mostrar_mensaje("Aviso", "Escribe un precio.")
            return
        try:
            precio = Decimal(texto)
            if not precio.is_finite() or precio < 0:
                raise InvalidOperation
        except InvalidOperation:
            self.mostrar_mensaje("Error", "Introduce un número válido mayor o igual a cero.")
            return

        self.precios_temporales.append(str(precio))
        self.precio_input.text = ""
        self.actualizar_precios_editor()

    def actualizar_precios_editor(self):
        self.precios_lista.clear_widgets()
        for indice, precio in enumerate(self.precios_temporales):
            fila = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            fila.add_widget(Label(
                text=money(precio),
                color=WHITE,
                halign="left"
            ))
            fila.add_widget(self.make_button(
                "Quitar", RED,
                lambda _btn, i=indice: self.quitar_precio(i),
                36
            ))
            self.precios_lista.add_widget(fila)

        total = sum((Decimal(p) for p in self.precios_temporales), Decimal("0"))
        self.total_editor_label.text = f"Total: {money(total)}"

    def quitar_precio(self, indice):
        del self.precios_temporales[indice]
        self.actualizar_precios_editor()

    def guardar_cliente(self, *_):
        nombre = self.nombre_input.text.strip()
        if not nombre:
            self.mostrar_mensaje("Aviso", "Escribe el nombre del cliente.")
            return

        nuevo = {
            "nombre": nombre,
            "precios": list(self.precios_temporales)
        }

        if self.cliente_editando is None:
            self.clientes.append(nuevo)
        else:
            self.clientes[self.cliente_editando] = nuevo

        self.guardar_datos_archivo()
        self.actualizar_lista()
        self.editor_popup.dismiss()

    def generar_pdf(self, *_):
        if not self.clientes:
            self.mostrar_mensaje("Aviso", "No hay clientes para imprimir.")
            return

        fecha = date.today().strftime("%d-%m-%Y")
        nombre_archivo = f"Totales-{fecha}.pdf"
        ruta = os.path.join(self.user_data_dir, nombre_archivo)

        try:
            documento = SimpleDocTemplate(
                ruta,
                pagesize=letter,
                rightMargin=36,
                leftMargin=36,
                topMargin=40,
                bottomMargin=40
            )

            elementos = []
            estilos = getSampleStyleSheet()
            elementos.append(Paragraph("Reporte de Clientes", estilos["Title"]))
            elementos.append(Spacer(1, 20))

            datos = [["Cliente", "Total"]]
            total_general = Decimal("0")

            for cliente in self.clientes:
                total = sum((Decimal(p) for p in cliente["precios"]), Decimal("0"))
                datos.append([cliente["nombre"], money(total)])
                total_general += total

            datos.append(["TOTAL GENERAL", money(total_general)])

            tabla = Table(datos, colWidths=[330, 150], repeatRows=1)
            tabla.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.whitesmoke]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]))
            elementos.append(tabla)
            elementos.append(Spacer(1, 18))
            elementos.append(Paragraph(
                f"Fecha: {fecha}",
                estilos["Normal"]
            ))
            documento.build(elementos)

            self.mostrar_mensaje(
                "PDF generado",
                "El reporte se creó correctamente.\n\n"
                f"Ubicación:\n{ruta}\n\n"
                "Está guardado dentro del almacenamiento privado de la aplicación."
            )
        except Exception as error:
            self.mostrar_mensaje("Error", f"No se pudo generar el PDF:\n{error}")


if __name__ == "__main__":
    import traceback

    try:
        SacarCuentasApp().run()
    except Exception:
        error = traceback.format_exc()

        # Guarda el error junto al archivo main para poder revisarlo.
        error_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_kivy.txt")
        try:
            with open(error_path, "w", encoding="utf-8") as archivo:
                archivo.write(error)
        except Exception:
            pass

        print("\\n===== ERROR DE SACAR CUENTAS =====\\n")
        print(error)
        print(f"\\nEl error también se guardó en: {error_path}")

        try:
            input("\\nPresiona ENTER para cerrar...")
        except EOFError:
            pass
