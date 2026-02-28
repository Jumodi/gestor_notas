import customtkinter as ctk
from customtkinter import CTk, CTkFrame, CTkLabel, CTkButton, CTkOptionMenu, CTkEntry, CTkScrollableFrame, CTkTabview, CTkInputDialog, CTkToplevel
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from database import DatabaseManager
from sync_file import FileSyncManager
import os
import threading
import platform
import time
import sys
from tkcalendar import Calendar
from datetime import datetime, date
import json
import statistics

SISTEMA = platform.system()

# Definición de colores del sistema
COLORES = {
    "primario": "#2C3E50",
    "secundario": "#34495E",
    "acento": "#3498DB",
    "exito": "#27AE60",
    "alerta": "#F39C12",
    "peligro": "#E74C3C",
    "fondo": "#ECF0F1",
    "tarjeta": "#FFFFFF",
    "texto": "#2C3E50",
    "texto_secundario": "#7F8C8D",
    "borde": "#BDC3C7"
}

def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, 'data')
    os.makedirs(data_path, exist_ok=True)
    return data_path

def get_token_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, 'token.json')

DATA_DIR = get_data_path()
DB_PATH = os.path.join(DATA_DIR, 'notas.db')
CREDENTIALS_PATH = os.path.join(get_executable_dir(), 'credentials.json')
TOKEN_PATH = get_token_path()

print(f"DEBUG: Buscando credentials en: {CREDENTIALS_PATH}")
print(f"DEBUG: Existe?: {os.path.exists(CREDENTIALS_PATH)}")

ctk.set_appearance_mode("System")

class GestorNotasApp(CTk):
    def __init__(self):
        super().__init__()
        
        # Configuración tipográfica
        self.FUENTES = {
            "titulo": ctk.CTkFont(family="Helvetica", size=20, weight="bold"),
            "subtitulo": ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            "normal": ctk.CTkFont(family="Helvetica", size=12),
            "pequeña": ctk.CTkFont(family="Helvetica", size=11),
            "boton": ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
            "monospace": ctk.CTkFont(family="Consolas", size=11)
        }
        
        self.title("Gestor de Evaluaciones Universitarias")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        self.db = DatabaseManager(DB_PATH)
        self.file_sync = FileSyncManager(DB_PATH)
        self.current_curso = None
        self.current_evaluacion = None
        self.entries_notas = {}
        self.auto_sync_enabled = False
        self.clase_actual_id = None
        
        self.setup_ui()
        self.load_cursos()
        self.after(1000, self.verificar_sincronizacion_inicio)

    def sincronizar_manual(self):
        """Abre dialogo de sincronizacion por archivo compartido"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Sincronizacion por Archivo Compartido")
        dialog.geometry("500x600")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"500x600+{x}+{y}")
        
        CTkLabel(dialog, text="Sincronizacion de Datos", 
                font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        
        estado, mensaje, info = self.file_sync.check_sync_status()
        
        frame_estado = CTkFrame(dialog)
        frame_estado.pack(fill="x", padx=20, pady=10)
        
        CTkLabel(frame_estado, text="Estado:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        
        color_estado = "green" if estado == "sincronizado" else "orange" if estado == "necesita_importar" else "red"
        lbl_estado = CTkLabel(frame_estado, text=mensaje, text_color=color_estado,
                             font=ctk.CTkFont(weight="bold"))
        lbl_estado.pack(anchor="w", padx=10, pady=5)
        
        if info:
            info_text = f"Ultima sync: {info.get('timestamp_sync', 'N/A')}\n"
            info_text += f"Dispositivo: {info.get('dispositivo_origen', 'N/A')}"
            CTkLabel(frame_estado, text=info_text, font=ctk.CTkFont(size=11), 
                    text_color="gray").pack(anchor="w", padx=10, pady=(0, 10))
        
        CTkLabel(dialog, text="Carpeta de sincronizacion:", 
                font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        folder_text = self.file_sync.sync_folder or "No configurada"
        lbl_folder = CTkLabel(dialog, text=folder_text, font=ctk.CTkFont(size=11))
        lbl_folder.pack(anchor="w", padx=20)
        
        btn_frame = CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        def exportar():
            success, msg = self.file_sync.export_to_sync()
            if success:
                messagebox.showinfo("Exito", msg)
                lbl_estado.configure(text="Sincronizado", text_color="green")
            else:
                messagebox.showerror("Error", msg)
        
        def importar():
            success, msg, info_extra = self.file_sync.import_from_sync()
            if success:
                if info_extra and info_extra != "sincronizado":
                    msg += f"\n\nExportado desde: {info_extra.get('dispositivo_origen', 'N/A')}"
                messagebox.showinfo("Exito", msg)
                self.load_cursos()
                lbl_estado.configure(text="Sincronizado", text_color="green")
            else:
                messagebox.showerror("Error", msg)
        
        CTkButton(btn_frame, text="Exportar a carpeta (Subir)", 
                 command=exportar, fg_color="blue", height=40).pack(fill="x", pady=5)
        CTkButton(btn_frame, text="Importar de carpeta (Descargar)", 
                 command=importar, fg_color="green", height=40).pack(fill="x", pady=5)
        
        CTkFrame(dialog, height=2, fg_color="gray").pack(fill="x", padx=20, pady=20)
        
        CTkLabel(dialog, text="Configuracion", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20)
        
        carpetas_default = self.file_sync.get_default_sync_paths()
        
        if carpetas_default:
            CTkLabel(dialog, text="Servicios detectados:", 
                    font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(10, 5))
            
            for nombre, ruta in carpetas_default:
                frame_servicio = CTkFrame(dialog)
                frame_servicio.pack(fill="x", padx=20, pady=2)
                
                CTkLabel(frame_servicio, text=nombre, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
                CTkLabel(frame_servicio, text=ruta, font=ctk.CTkFont(size=10)).pack(side="left", padx=5)
                
                def usar_ruta(r=ruta):
                    success, msg = self.file_sync.setup_sync_folder(r)
                    if success:
                        lbl_folder.configure(text=r)
                        messagebox.showinfo("Exito", msg)
                    else:
                        messagebox.showerror("Error", msg)
                
                CTkButton(frame_servicio, text="Usar", width=60, 
                         command=usar_ruta).pack(side="right", padx=5)
        
        def seleccionar_carpeta():
            folder = filedialog.askdirectory(title="Seleccionar carpeta de sincronizacion")
            if folder:
                success, msg = self.file_sync.setup_sync_folder(folder)
                if success:
                    lbl_folder.configure(text=folder)
                    messagebox.showinfo("Exito", msg)
                else:
                    messagebox.showerror("Error", msg)
        
        CTkButton(dialog, text="Seleccionar carpeta manualmente...", 
                 command=seleccionar_carpeta).pack(fill="x", padx=20, pady=10)
        
        if estado == "conflicto":
            CTkFrame(dialog, height=2, fg_color="red").pack(fill="x", padx=20, pady=20)
            
            CTkLabel(dialog, text="Conflicto detectado", 
                    font=ctk.CTkFont(size=14, weight="bold"), text_color="red").pack(anchor="w", padx=20)
            
            CTkLabel(dialog, text="Ambas versiones tienen cambios. Elige cual conservar:", 
                    font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=5)
            
            conflict_frame = CTkFrame(dialog)
            conflict_frame.pack(fill="x", padx=20, pady=10)
            
            def resolver_usar_local():
                if messagebox.askyesno("Confirmar", "Esto sobrescribira la version en la carpeta compartida con tu version local. Continuar?"):
                    success, msg = self.file_sync.resolver_conflicto(usar_local=True)
                    messagebox.showinfo("Resultado", msg)
                    if success:
                        lbl_estado.configure(text="Sincronizado", text_color="green")
            
            def resolver_usar_nube():
                if messagebox.askyesno("Confirmar", "Esto sobrescribira tu base de datos local con la version de la carpeta compartida. Continuar?"):
                    success, msg, _ = self.file_sync.resolver_conflicto(usar_local=False)
                    messagebox.showinfo("Resultado", msg)
                    if success:
                        self.load_cursos()
                        lbl_estado.configure(text="Sincronizado", text_color="green")
            
            CTkButton(conflict_frame, text="Usar version LOCAL (subir)", 
                     command=resolver_usar_local, fg_color="orange", height=35).pack(fill="x", pady=5)
            CTkButton(conflict_frame, text="Usar version de CARPETA (descargar)", 
                     command=resolver_usar_nube, fg_color="orange", height=35).pack(fill="x", pady=5)
        
        CTkButton(dialog, text="Cerrar", command=dialog.destroy, 
                 fg_color="gray").pack(pady=20)

    def verificar_sincronizacion_inicio(self):
        """Verifica el estado de sincronizacion al iniciar la aplicacion"""
        estado, mensaje, info = self.file_sync.check_sync_status()
        
        if estado == "necesita_importar":
            respuesta = messagebox.askyesno(
                "Sincronizacion", 
                f"Hay una version mas reciente en la carpeta compartida.\n"
                f"Dispositivo origen: {info.get('dispositivo_origen', 'N/A')}\n"
                f"Fecha: {info.get('timestamp_sync', 'N/A')}\n\n"
                f"Deseas importar los cambios ahora?"
            )
            if respuesta:
                success, msg, _ = self.file_sync.import_from_sync()
                if success:
                    messagebox.showinfo("Exito", "Datos importados correctamente.\nLa aplicacion se actualizara.")
                    self.load_cursos()
                else:
                    messagebox.showerror("Error", msg)
        
        elif estado == "conflicto":
            messagebox.showwarning(
                "Conflicto de sincronizacion",
                "Se detectaron cambios tanto en tu dispositivo como en la carpeta compartida.\n"
                "Ve a Herramientas > Sincronizar para resolver el conflicto."
            )
        
        if estado == "sincronizado":
            self.status_label.configure(text="Sync: Sincronizado", text_color="green")
        elif estado == "no_config":
            self.status_label.configure(text="Sync: Sin configurar", text_color="gray")
        else:
            self.status_label.configure(text=f"Sync: {mensaje[:30]}...", text_color="orange")

    def crear_curso(self):
        dialog = CTkInputDialog(text="Nombre del nuevo curso:", title="Crear Curso")
        nombre = dialog.get_input()
        if nombre and nombre.strip():
            nombre = nombre.strip()
            dialog2 = CTkInputDialog(text="Descripcion (opcional):", title="Crear Curso")
            descripcion = dialog2.get_input() or ""
            curso_id, error = self.db.crear_curso(nombre, descripcion)
            if curso_id:
                messagebox.showinfo("Exito", f"Curso '{nombre}' creado correctamente. Ahora agrega evaluaciones y estudiantes.")
                self.load_cursos()
            else:
                messagebox.showerror("Error", error or "No se pudo crear el curso")

    def seleccionar_curso(self, nombre_curso):
        for nombre, btn in self.curso_buttons.items():
            btn.configure(fg_color=COLORES["secundario"], 
                         text_color="white")
        if nombre_curso in self.curso_buttons:
            self.curso_buttons[nombre_curso].configure(
                fg_color=COLORES["acento"],
                text_color="white"
            )
        self.current_curso = self.cursos_data.get(nombre_curso)
        if self.current_curso:
            self.load_evaluaciones()
            self.actualizar_info_curso()
            self.actualizar_config_curso()
            self.actualizar_resumen()
            self.cargar_lista_clases()  
            self.limpiar_campos_clase()  
            self.clase_actual_id = None

    def load_cursos(self):
        for widget in self.cursos_scroll.winfo_children():
            widget.destroy()
        
        cursos = self.db.get_cursos()
        self.cursos_data = {}
        self.curso_buttons = {}
        
        if cursos:
            for curso in cursos:
                curso_id, nombre, descripcion, total_est, total_eval = curso
                self.cursos_data[nombre] = curso_id
                
                btn_frame = CTkFrame(self.cursos_scroll, 
                                    fg_color="transparent")
                btn_frame.pack(fill="x", pady=2)
                
                btn = CTkButton(
                    btn_frame, 
                    text=f"{nombre}\n{total_est} estudiantes · {total_eval} evaluaciones", 
                    command=lambda n=nombre: self.seleccionar_curso(n),
                    fg_color=COLORES["secundario"],
                    border_width=0,
                    hover_color=COLORES["acento"],
                    anchor="w",
                    height=50,
                    corner_radius=6,
                    font=self.FUENTES["pequeña"],
                    text_color="white"
                )
                btn.pack(fill="x", padx=2, pady=2)
                
                self.curso_buttons[nombre] = btn
                
            self.seleccionar_curso(cursos[0][1])
        else:
            CTkLabel(self.cursos_scroll, 
                    text="No hay cursos registrados",
                    font=self.FUENTES["pequeña"],
                    text_color=COLORES["texto_secundario"]).pack(pady=20)
            self.current_curso = None

    def editar_curso(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        cursos = self.db.get_cursos()
        curso = next((c for c in cursos if c[0] == self.current_curso), None)
        dialog = CTkInputDialog(text="Nuevo nombre del curso:", title="Editar Curso")
        dialog._input.insert(0, curso[1])
        nuevo_nombre = dialog.get_input()
        if nuevo_nombre and nuevo_nombre.strip():
            nuevo_nombre = nuevo_nombre.strip()
            dialog2 = CTkInputDialog(text="Nueva descripcion:", title="Editar Curso")
            dialog2._input.insert(0, curso[2] or "")
            nueva_desc = dialog2.get_input()
            success, error = self.db.actualizar_curso(self.current_curso, nuevo_nombre, nueva_desc)
            if success:
                messagebox.showinfo("Exito", "Curso actualizado correctamente")
                self.load_cursos()
            else:
                messagebox.showerror("Error", error or "No se pudo actualizar")

    def eliminar_curso(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        curso_nombre = None
        for nombre, cid in self.cursos_data.items():
            if cid == self.current_curso:
                curso_nombre = nombre
                break
        if messagebox.askyesno("Confirmar", f"Eliminar permanentemente el curso '{curso_nombre}'? Se perderan TODOS los datos (evaluaciones, estudiantes y notas)."):
            success, error = self.db.eliminar_curso(self.current_curso)
            if success:
                messagebox.showinfo("Exito", "Curso eliminado correctamente")
                self.current_curso = None
                self.current_evaluacion = None
                self.load_cursos()
                self.limpiar_interfaz()
            else:
                messagebox.showerror("Error", error or "No se pudo eliminar el curso")

    def seleccionar_evaluacion(self, nombre_eval):
        for nombre, btn in self.eval_buttons.items():
            btn.configure(fg_color=COLORES["secundario"],
                         text_color="white")
        if nombre_eval in self.eval_buttons:
            self.eval_buttons[nombre_eval].configure(
                fg_color=COLORES["exito"],
                text_color="white"
            )
        self.current_evaluacion = self.evals_data.get(nombre_eval)
        if self.current_evaluacion:
            self.load_estudiantes_notas()
        else:
            self.limpiar_tab_notas()

    def load_evaluaciones(self):
        if not self.current_curso:
            return
        
        for widget in self.evals_scroll.winfo_children():
            widget.destroy()
        
        evals = self.db.get_evaluaciones(self.current_curso)
        self.evals_data = {}
        self.eval_buttons = {}
        
        if evals:
            for eval in evals:
                eval_id, nombre, puntos_max, orden, fecha = eval
                self.evals_data[nombre] = eval_id
                
                btn_frame = CTkFrame(self.evals_scroll, 
                                    fg_color="transparent")
                btn_frame.pack(fill="x", pady=2)
                
                btn = CTkButton(
                    btn_frame,
                    text=f"{orden}. {nombre}\nMáximo: {puntos_max} puntos",
                    command=lambda n=nombre: self.seleccionar_evaluacion(n),
                    fg_color=COLORES["secundario"],
                    border_width=0,
                    hover_color=COLORES["exito"],
                    anchor="w",
                    height=45,
                    corner_radius=6,
                    font=self.FUENTES["pequeña"],
                    text_color="white"
                )
                btn.pack(fill="x", padx=2, pady=2)
                
                self.eval_buttons[nombre] = btn
            
            self.seleccionar_evaluacion(evals[0][1])
        else:
            CTkLabel(self.evals_scroll, 
                    text="Sin evaluaciones configuradas",
                    font=self.FUENTES["pequeña"],
                    text_color=COLORES["texto_secundario"]).pack(pady=20)
            self.current_evaluacion = None
            self.limpiar_tab_notas()

    def agregar_evaluacion(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        dialog = CTkInputDialog(text="Nombre de la evaluacion:", title="Nueva Evaluacion")
        nombre = dialog.get_input()
        if nombre and nombre.strip():
            nombre = nombre.strip()
            dialog2 = CTkInputDialog(text="Porcentaje (%):", title="Nueva Evaluacion")
            try:
                porcentaje_str = dialog2.get_input()
                porcentaje = float(porcentaje_str) if porcentaje_str else 0
                if porcentaje <= 0 or porcentaje > 100:
                    raise ValueError
            except:
                messagebox.showerror("Error", "Porcentaje invalido. Debe ser entre 1 y 100.")
                return
            total_actual = self.db.verificar_porcentaje_total(self.current_curso)
            if total_actual + porcentaje > 100:
                messagebox.showerror("Error", f"El total de puntos sería {total_actual + porcentaje}. El máximo permitido es 100 puntos. Puntos actuales asignados: {total_actual}")
                return
            eval_id, error = self.db.agregar_evaluacion(self.current_curso, nombre, porcentaje)
            if eval_id:
                messagebox.showinfo("Exito", f"Evaluacion '{nombre}' agregada (Máximo: {porcentaje} puntos)")
                self.load_evaluaciones()
                self.actualizar_config_curso()
            else:
                messagebox.showerror("Error", error or "No se pudo agregar la evaluacion")

    def editar_evaluacion(self):
        if not self.current_evaluacion:
            messagebox.showwarning("Advertencia", "Selecciona una evaluacion primero")
            return
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_actual = next((e for e in evals if e[0] == self.current_evaluacion), None)
        if not eval_actual:
            return
        dialog = CTkInputDialog(text="Nuevo nombre de la evaluacion:", title="Editar Evaluacion")
        dialog._input.insert(0, eval_actual[1])
        nuevo_nombre = dialog.get_input()
        if nuevo_nombre and nuevo_nombre.strip():
            nuevo_nombre = nuevo_nombre.strip()
            dialog2 = CTkInputDialog(text=f"Nuevo porcentaje (actual: {eval_actual[2]}%):", title="Editar Evaluacion")
            dialog2._input.insert(0, str(eval_actual[2]))
            try:
                nuevo_pct = float(dialog2.get_input() or eval_actual[2])
            except:
                nuevo_pct = eval_actual[2]
            total_actual = self.db.verificar_porcentaje_total(self.current_curso)
            total_sin_esta = total_actual - eval_actual[2]
            if total_sin_esta + nuevo_pct > 100:
                messagebox.showerror("Error", f"El total seria {total_sin_esta + nuevo_pct}%. Maximo permitido: 100%")
                return
            success, error = self.db.actualizar_evaluacion(self.current_evaluacion, nuevo_nombre, nuevo_pct)
            if success:
                messagebox.showinfo("Exito", "Evaluacion actualizada")
                self.load_evaluaciones()
                self.actualizar_config_curso()
            else:
                messagebox.showerror("Error", error or "No se pudo actualizar")

    def eliminar_evaluacion(self):
        if not self.current_evaluacion:
            messagebox.showwarning("Advertencia", "Selecciona una evaluacion primero")
            return
        eval_nombre = None
        for nombre, eid in self.evals_data.items():
            if eid == self.current_evaluacion:
                eval_nombre = nombre
                break
        if messagebox.askyesno("Confirmar", f"Eliminar la evaluacion '{eval_nombre}'? Se perderan las notas asociadas."):
            success, error = self.db.eliminar_evaluacion(self.current_evaluacion)
            if success:
                messagebox.showinfo("Exito", "Evaluacion eliminada")
                self.load_evaluaciones()
                self.actualizar_config_curso()
            else:
                messagebox.showerror("Error", error or "No se pudo eliminar")

    def editar_rubrica(self):
        if not self.current_evaluacion:
            messagebox.showwarning("Advertencia", "Seleccione una evaluación primero")
            return
        
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
        if not eval_info:
            return
        
        eval_nombre = eval_info[1]
        puntos_max_eval = eval_info[2]
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Editar Rúbrica - {eval_nombre}")
        dialog.geometry("700x600")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"700x600+{x}+{y}")
        
        CTkLabel(dialog,
                text=f"RÚBRICA: {eval_nombre}",
                font=self.FUENTES["titulo"],
                text_color=COLORES["texto"]).pack(pady=(20, 5))
        
        CTkLabel(dialog,
                text=f"Puntos máximos de la evaluación: {puntos_max_eval}",
                font=self.FUENTES["normal"],
                text_color=COLORES["texto_secundario"]).pack()
        
        frame_total = CTkFrame(dialog,
                              fg_color=COLORES["fondo"],
                              corner_radius=8)
        frame_total.pack(fill="x", padx=20, pady=10)
        
        self.lbl_total_rubrica = CTkLabel(frame_total,
                                         text="Total asignado en rúbrica: 0",
                                         font=self.FUENTES["subtitulo"],
                                         text_color=COLORES["texto"])
        self.lbl_total_rubrica.pack(side="left", padx=15, pady=10)
        
        self.lbl_diferencia = CTkLabel(frame_total,
                                      text="(Faltan: 20)",
                                      font=self.FUENTES["normal"],
                                      text_color=COLORES["alerta"])
        self.lbl_diferencia.pack(side="left", padx=10)
        
        scroll_criterios = CTkScrollableFrame(dialog,
                                             fg_color=COLORES["tarjeta"],
                                             height=350,
                                             corner_radius=8)
        scroll_criterios.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.frame_criterios_list = scroll_criterios
        self.criterios_entries = []
        
        def actualizar_total():
            total = 0
            for entry_info in self.criterios_entries:
                try:
                    puntos = float(entry_info['puntos'].get() or 0)
                    total += puntos
                except:
                    pass
            
            self.lbl_total_rubrica.configure(text=f"Total asignado: {total}")
            
            diferencia = puntos_max_eval - total
            if diferencia == 0:
                color = COLORES["exito"]
                texto = "(Completo)"
            elif diferencia > 0:
                color = COLORES["alerta"]
                texto = f"(Faltan: {diferencia})"
            else:
                color = COLORES["peligro"]
                texto = f"(Excede por: {abs(diferencia)})"
            
            self.lbl_diferencia.configure(text=texto, text_color=color)
        
        def agregar_fila_criterio(nombre="", puntos="", criterio_id=None):
            frame = CTkFrame(self.frame_criterios_list,
                            fg_color=COLORES["fondo"],
                            corner_radius=6)
            frame.pack(fill="x", pady=3, padx=2)
            
            entry_nombre = CTkEntry(frame,
                                   placeholder_text="Nombre del criterio",
                                   width=350,
                                   font=self.FUENTES["normal"],
                                   fg_color=COLORES["tarjeta"],
                                   text_color=COLORES["texto"],
                                   border_color=COLORES["borde"])
            entry_nombre.pack(side="left", padx=5, pady=5, fill="x", expand=True)
            if nombre:
                entry_nombre.insert(0, nombre)
            
            entry_puntos = CTkEntry(frame,
                                   placeholder_text="Pts",
                                   width=80,
                                   font=self.FUENTES["normal"],
                                   fg_color=COLORES["tarjeta"],
                                   text_color=COLORES["texto"],
                                   border_color=COLORES["borde"])
            entry_puntos.pack(side="left", padx=5, pady=5)
            if puntos:
                entry_puntos.insert(0, str(puntos))
            
            criterio_info = {
                'frame': frame,
                'nombre': entry_nombre,
                'puntos': entry_puntos,
                'id': criterio_id
            }
            self.criterios_entries.append(criterio_info)
            
            entry_puntos.bind("<KeyRelease>", lambda e: actualizar_total())
            
            def eliminar_fila():
                frame.destroy()
                self.criterios_entries.remove(criterio_info)
                actualizar_total()
                if criterio_id:
                    criterio_info['eliminar'] = True
            
            CTkButton(frame,
                     text="X",
                     width=30,
                     command=eliminar_fila,
                     fg_color=COLORES["peligro"],
                     hover_color="#A93226",
                     font=self.FUENTES["boton"],
                     height=28).pack(side="left", padx=5, pady=5)
        
        criterios_existentes = self.db.get_criterios_rubrica(self.current_evaluacion)
        if criterios_existentes:
            for crit in criterios_existentes:
                crit_id, nombre, puntos, orden = crit
                agregar_fila_criterio(nombre, puntos, crit_id)
        else:
            agregar_fila_criterio()
            agregar_fila_criterio()
        
        actualizar_total()
        
        CTkButton(dialog,
                 text="+ Agregar Criterio",
                 command=lambda: agregar_fila_criterio(),
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"],
                 height=32).pack(pady=5)
        
        btn_frame = CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        def guardar_rubrica():
            total = 0
            criterios_validos = []
            
            for entry_info in self.criterios_entries:
                nombre = entry_info['nombre'].get().strip()
                try:
                    puntos = float(entry_info['puntos'].get() or 0)
                except:
                    puntos = 0
                
                if nombre:
                    total += puntos
                    criterios_validos.append({
                        'nombre': nombre,
                        'puntos': puntos,
                        'id': entry_info.get('id'),
                        'eliminar': entry_info.get('eliminar', False)
                    })
            
            if total != puntos_max_eval:
                messagebox.showerror("Error",
                    f"Los puntos de la rúbrica deben sumar exactamente {puntos_max_eval}.\n"
                    f"Actualmente suman: {total}")
                return
            
            try:
                for c in criterios_validos:
                    if c['eliminar'] and c['id']:
                        self.db.eliminar_criterio_rubrica(c['id'])
                
                for idx, c in enumerate(criterios_validos):
                    if not c['eliminar']:
                        if c['id']:
                            self.db.actualizar_criterio_rubrica(c['id'], c['nombre'], c['puntos'], idx)
                        else:
                            self.db.agregar_criterio_rubrica(
                                self.current_evaluacion,
                                c['nombre'],
                                c['puntos'],
                                idx
                            )
                
                messagebox.showinfo("Éxito", "Rúbrica guardada correctamente")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
        
        CTkButton(btn_frame,
                 text="Guardar Rúbrica",
                 command=guardar_rubrica,
                 fg_color=COLORES["exito"],
                 hover_color="#219A52",
                 height=40,
                 font=self.FUENTES["boton"]).pack(side="left", padx=5, fill="x", expand=True)
        
        CTkButton(btn_frame,
                 text="Cancelar",
                 command=dialog.destroy,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 height=40,
                 font=self.FUENTES["boton"]).pack(side="left", padx=5, fill="x", expand=True)

    def agregar_estudiante(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Seleccione un curso primero")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nuevo Estudiante")
        dialog.geometry("450x450")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f"450x450+{x}+{y}")
        
        frame = CTkFrame(dialog, fg_color=COLORES["fondo"])
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        CTkLabel(frame,
                text="NUEVO ESTUDIANTE",
                font=self.FUENTES["subtitulo"],
                text_color=COLORES["texto"]).pack(pady=(15, 20))
        
        campos_frame = CTkFrame(frame,
                               fg_color=COLORES["tarjeta"],
                               corner_radius=8)
        campos_frame.pack(fill="x", padx=10, pady=5)
        
        CTkLabel(campos_frame,
                text="Nombre completo *",
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(anchor="w", padx=15, pady=(15, 5))
        entry_nombre = CTkEntry(campos_frame,
                               width=380,
                               placeholder_text="Ej: Juan Pérez García",
                               font=self.FUENTES["normal"],
                               fg_color=COLORES["tarjeta"],
                               text_color=COLORES["texto"],
                               border_color=COLORES["borde"])
        entry_nombre.pack(fill="x", padx=15, pady=5)
        
        CTkLabel(campos_frame,
                text="Número de carné",
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(anchor="w", padx=15, pady=(10, 5))
        entry_carne = CTkEntry(campos_frame,
                              width=380,
                              placeholder_text="Ej: 20240001",
                              font=self.FUENTES["normal"],
                              fg_color=COLORES["tarjeta"],
                              text_color=COLORES["texto"],
                              border_color=COLORES["borde"])
        entry_carne.pack(fill="x", padx=15, pady=5)
        
        CTkLabel(campos_frame,
                text="Grupo *",
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(anchor="w", padx=15, pady=(10, 5))
        entry_grupo = CTkEntry(campos_frame,
                              width=380,
                              placeholder_text="1",
                              font=self.FUENTES["normal"],
                              fg_color="white",
                              border_color=COLORES["borde"])
        entry_grupo.insert(0, "1")
        entry_grupo.pack(fill="x", padx=15, pady=5)
        
        CTkLabel(campos_frame,
                text="Correo electrónico",
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(anchor="w", padx=15, pady=(10, 5))
        entry_email = CTkEntry(campos_frame,
                              width=380,
                              placeholder_text="ejemplo@universidad.edu",
                              font=self.FUENTES["normal"],
                              fg_color="white",
                              border_color=COLORES["borde"])
        entry_email.pack(fill="x", padx=15, pady=(5, 15))
        
        CTkLabel(frame,
                text="* Campos obligatorios",
                font=self.FUENTES["pequeña"],
                text_color=COLORES["texto_secundario"]).pack(pady=5)
        
        def guardar():
            nombre = entry_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre es obligatorio")
                return
            
            try:
                grupo = int(entry_grupo.get().strip() or 1)
            except:
                grupo = 1
            
            carne = entry_carne.get().strip() or None
            email = entry_email.get().strip() or None
            
            est_id, error = self.db.agregar_estudiante(self.current_curso, nombre, grupo, email, carne)
            
            if est_id:
                messagebox.showinfo("Éxito", f"Estudiante '{nombre}' agregado al Grupo {grupo}")
                dialog.destroy()
                self.load_estudiantes_notas()
                self.actualizar_resumen()
                self.load_cursos()
            else:
                messagebox.showerror("Error", error or "No se pudo agregar el estudiante")
        
        CTkButton(frame,
                 text="Guardar Estudiante",
                 command=guardar,
                 fg_color=COLORES["exito"],
                 hover_color="#219A52",
                 height=40,
                 font=self.FUENTES["boton"]).pack(pady=15)

    def agregar_varios_estudiantes(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Agregar Varios Estudiantes")
        dialog.geometry("500x500")
        dialog.transient(self)
        dialog.grab_set()
        
        CTkLabel(dialog, text="Agregar Varios Estudiantes", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))
        
        CTkLabel(dialog, text="Grupo para todos los estudiantes:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
        entry_grupo = CTkEntry(dialog, width=100, placeholder_text="1")
        entry_grupo.insert(0, "1")
        entry_grupo.pack(pady=5)
        
        CTkLabel(dialog, text="Ingresa los nombres (uno por línea):", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        
        text_box = ctk.CTkTextbox(dialog, width=450, height=250)
        text_box.pack(pady=10, padx=20)
        
        def guardar():
            try:
                grupo = int(entry_grupo.get().strip() or 1)
            except:
                grupo = 1
            
            nombres = text_box.get("1.0", "end").strip().split("\n")
            nombres = [n.strip() for n in nombres if n.strip()]
            agregados = 0
            
            for nombre in nombres:
                est_id, _ = self.db.agregar_estudiante(self.current_curso, nombre, grupo, None, None)
                if est_id:
                    agregados += 1
            
            messagebox.showinfo("Éxito", f"{agregados} estudiantes agregados al Grupo {grupo}")
            dialog.destroy()
            self.load_estudiantes_notas()
            self.actualizar_resumen()
            self.load_cursos()
        
        CTkButton(dialog, text="Agregar Todos", command=guardar, 
                 fg_color="green", hover_color="darkgreen",
                 height=40, font=ctk.CTkFont(weight="bold")).pack(pady=15)

    def editar_estudiante(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        estudiantes = self.db.get_estudiantes(self.current_curso)
        if not estudiantes:
            messagebox.showinfo("Info", "No hay estudiantes en este curso")
            return
        
        lista_info = []
        for est in estudiantes:
            est_id, nombre, grupo, email, carne = est
            display = f"{nombre} (G{grupo})"
            lista_info.append((display, est))
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar Estudiante")
        dialog.geometry("500x500")
        dialog.transient(self)
        dialog.grab_set()
        
        CTkLabel(dialog, text="Selecciona estudiante a editar:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        nombres = [info[0] for info in lista_info]
        est_var = ctk.StringVar(value=nombres[0])
        menu = CTkOptionMenu(dialog, values=nombres, variable=est_var, width=400)
        menu.pack(pady=10)
        
        frame_edit = CTkFrame(dialog)
        frame_edit.pack(fill="x", padx=30, pady=10)
        
        entry_nombre_var = ctk.StringVar()
        entry_carne_var = ctk.StringVar()
        entry_grupo_var = ctk.StringVar()
        entry_email_var = ctk.StringVar()
        
        def cargar_datos_seleccion(*args):
            seleccion = est_var.get()
            est = None
            for display, est_data in lista_info:
                if display == seleccion:
                    est = est_data
                    break
            
            if est:
                est_id, nombre, grupo, email, carne = est
                entry_nombre_var.set(nombre)
                entry_carne_var.set(carne or "")
                entry_grupo_var.set(str(grupo))
                entry_email_var.set(email or "")
        
        CTkLabel(frame_edit, text="Nombre:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        entry_nombre = CTkEntry(frame_edit, width=400, textvariable=entry_nombre_var)
        entry_nombre.pack(fill="x", pady=2)
        
        CTkLabel(frame_edit, text="Carné:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,0))
        entry_carne = CTkEntry(frame_edit, width=400, textvariable=entry_carne_var)
        entry_carne.pack(fill="x", pady=2)
        
        CTkLabel(frame_edit, text="Grupo:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,0))
        entry_grupo = CTkEntry(frame_edit, width=400, textvariable=entry_grupo_var)
        entry_grupo.pack(fill="x", pady=2)
        
        CTkLabel(frame_edit, text="Email:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,0))
        entry_email = CTkEntry(frame_edit, width=400, textvariable=entry_email_var)
        entry_email.pack(fill="x", pady=2)
        
        cargar_datos_seleccion()
        est_var.trace_add("write", cargar_datos_seleccion)
        
        def guardar_cambios():
            seleccion = est_var.get()
            est_id = None
            for display, est_data in lista_info:
                if display == seleccion:
                    est_id = est_data[0]
                    break
            
            if not est_id:
                return
            
            nuevo_nombre = entry_nombre_var.get().strip()
            nuevo_carne = entry_carne_var.get().strip() or None
            try:
                nuevo_grupo = int(entry_grupo_var.get())
            except:
                nuevo_grupo = 1
            nuevo_email = entry_email_var.get().strip() or None
            
            success, error = self.db.actualizar_estudiante(
                est_id, nuevo_nombre, nuevo_grupo, nuevo_email, nuevo_carne
            )
            
            if success:
                messagebox.showinfo("Éxito", "Estudiante actualizado")
                dialog.destroy()
                self.load_estudiantes_notas()
                self.actualizar_resumen()
                self.load_cursos()
            else:
                messagebox.showerror("Error", error or "No se pudo actualizar")
        
        CTkButton(dialog, text="Guardar Cambios", command=guardar_cambios,
                 fg_color="green", hover_color="darkgreen", 
                 height=40, font=ctk.CTkFont(weight="bold")).pack(pady=20)

    def eliminar_estudiante(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        estudiantes = self.db.get_estudiantes(self.current_curso)
        if not estudiantes:
            messagebox.showinfo("Info", "No hay estudiantes en este curso")
            return
        nombres = [f"{e[1]} (ID:{e[0]})" for e in estudiantes]
        dialog = ctk.CTkToplevel(self)
        dialog.title("Eliminar Estudiante")
        dialog.geometry("400x300")
        dialog.transient(self)
        CTkLabel(dialog, text="Selecciona estudiante a eliminar:", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        est_var = ctk.StringVar(value=nombres[0])
        menu = CTkOptionMenu(dialog, values=nombres, variable=est_var, width=350)
        menu.pack(pady=10)
        def confirmar():
            seleccion = est_var.get()
            est_id = int(seleccion.split("(ID:")[1].replace(")", ""))
            nombre = seleccion.split(" (ID:")[0]
            if messagebox.askyesno("Confirmar", f"Eliminar a '{nombre}' permanentemente?"):
                success, _ = self.db.eliminar_estudiante(est_id)
                if success:
                    messagebox.showinfo("Exito", "Estudiante eliminado")
                    dialog.destroy()
                    self.load_estudiantes_notas()
                    self.actualizar_resumen()
                    self.load_cursos()
        CTkButton(dialog, text="Eliminar", command=confirmar, fg_color="red", hover_color="darkred").pack(pady=20)

    def load_estudiantes_notas(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        self.entries_notas = {}
        
        if not self.current_curso:
            CTkLabel(self.scroll_frame, 
                    text="Seleccione un curso para comenzar", 
                    font=self.FUENTES["normal"],
                    text_color=COLORES["texto_secundario"]).pack(pady=40)
            return
        
        if not self.current_evaluacion:
            CTkLabel(self.scroll_frame, 
                    text="Seleccione una evaluación para ver estudiantes", 
                    font=self.FUENTES["normal"],
                    text_color=COLORES["texto_secundario"]).pack(pady=40)
            return
        
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
        
        if not eval_info:
            return
        
        eval_nombre = eval_info[1]
        eval_puntos_max = eval_info[2]
        
        header_frame = CTkFrame(self.scroll_frame, 
                               fg_color=COLORES["primario"],
                               corner_radius=8)
        header_frame.pack(fill="x", padx=5, pady=(0, 15))
        
        CTkLabel(header_frame, 
                text=f"{eval_nombre}",
                font=self.FUENTES["subtitulo"],
                text_color="white").pack(side="left", padx=15, pady=12)
        
        CTkLabel(header_frame, 
                text=f"Máximo: {eval_puntos_max} puntos",
                font=self.FUENTES["normal"],
                text_color=COLORES["texto_secundario"]).pack(side="right", padx=15)
        
        self.guardado_status_label = CTkLabel(header_frame, 
                                              text="Listo", 
                                              font=self.FUENTES["pequeña"],
                                              text_color=COLORES["exito"])
        self.guardado_status_label.pack(side="right", padx=10)
        
        todos_estudiantes = self.db.get_estudiantes(self.current_curso)
        
        if not todos_estudiantes:
            CTkLabel(self.scroll_frame, 
                    text="No hay estudiantes registrados en este curso", 
                    font=self.FUENTES["normal"],
                    text_color=COLORES["texto_secundario"]).pack(pady=40)
            return
        
        grupos = {}
        for est in todos_estudiantes:
            grupo_num = est[2]
            if grupo_num not in grupos:
                grupos[grupo_num] = []
            grupos[grupo_num].append(est)
        
        self.tabview_grupos = CTkTabview(self.scroll_frame,
                                        fg_color=COLORES["fondo"],
                                        segmented_button_fg_color=COLORES["secundario"],
                                        segmented_button_selected_color=COLORES["acento"],
                                        segmented_button_selected_hover_color="#2980B9",
                                        segmented_button_unselected_color=COLORES["secundario"],
                                        text_color=COLORES["texto"])
        self.tabview_grupos.pack(fill="both", expand=True, padx=5, pady=5)
        
        for grupo_num in sorted(grupos.keys()):
            estudiantes_grupo = grupos[grupo_num]
            tab_nombre = f"Grupo {grupo_num}"
            
            tab = self.tabview_grupos.add(tab_nombre)
            self.crear_contenido_grupo(tab, estudiantes_grupo, eval_puntos_max)
        
        self.status_label.configure(text=f"{len(todos_estudiantes)} estudiantes · {len(grupos)} grupos",
                                   text_color=COLORES["texto_secundario"])

    def crear_contenido_grupo(self, tab_padre, estudiantes, puntos_max):
        container = CTkFrame(tab_padre, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        header = CTkFrame(container, fg_color=COLORES["secundario"], corner_radius=6)
        header.pack(fill="x", padx=5, pady=(0, 10))
        
        CTkLabel(header, text="ESTUDIANTE", 
                font=self.FUENTES["boton"],
                text_color="white").pack(side="left", padx=15, pady=10)
        CTkLabel(header, text="NOTA", 
                font=self.FUENTES["boton"],
                text_color="white").pack(side="left", padx=80)
        CTkLabel(header, text="OBSERVACIONES", 
                font=self.FUENTES["boton"],
                text_color="white").pack(side="left", padx=20)
        
        scroll_grupo = CTkScrollableFrame(container, 
                                         fg_color="transparent",
                                         height=450)
        scroll_grupo.pack(fill="both", expand=True)
        
        for idx, est in enumerate(estudiantes):
            est_id, nombre, grupo_num, email, carne = est
            
            bg_color = COLORES["tarjeta"] if idx % 2 == 0 else COLORES["fondo"]
            
            row = CTkFrame(scroll_grupo, fg_color=bg_color, corner_radius=4)
            row.pack(fill="x", pady=1, padx=5)
            row.pack_propagate(False)
            row.configure(height=42)
            
            nombre_container = CTkFrame(row, fg_color="transparent", width=280)
            nombre_container.pack(side="left", padx=10, pady=5)
            nombre_container.pack_propagate(False)
            
            lbl_nombre = CTkLabel(nombre_container, 
                                 text=nombre,
                                 font=self.FUENTES["normal"],
                                 text_color=COLORES["texto"],
                                 cursor="hand2")
            lbl_nombre.pack(anchor="w")
            
            lbl_nombre.bind("<Button-1>", 
                           lambda e, est=est: self.mostrar_modal_estudiante(est))
            
            def on_enter(e, widget=lbl_nombre):
                widget.configure(text_color=COLORES["acento"], 
                               font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"))
            def on_leave(e, widget=lbl_nombre):
                widget.configure(text_color=COLORES["texto"], 
                               font=self.FUENTES["normal"])
            
            lbl_nombre.bind("<Enter>", on_enter)
            lbl_nombre.bind("<Leave>", on_leave)
            
            nota_existente, obs_existente = self.db.get_nota(est_id, self.current_evaluacion)
            tiene_rubrica = len(self.db.get_criterios_rubrica(self.current_evaluacion)) > 0
            
            nota_container = CTkFrame(row, fg_color="transparent", width=120)
            nota_container.pack(side="left", padx=5, pady=5)
            
            nota_var = ctk.StringVar(value=str(nota_existente) if nota_existente is not None else "")
            entry_nota = CTkEntry(nota_container, width=70, 
                                 textvariable=nota_var,
                                 justify="center",
                                 font=self.FUENTES["normal"],
                                 fg_color=COLORES["tarjeta"],
                                 text_color=COLORES["texto"],
                                 border_color=COLORES["borde"])
            entry_nota.pack(side="left", padx=2)
            
            if tiene_rubrica and nota_existente:
                estado_text = "R"
                estado_color = COLORES["acento"]
            elif nota_existente:
                estado_text = "OK"
                estado_color = COLORES["exito"]
            else:
                estado_text = "-"
                estado_color = COLORES["texto_secundario"]
            
            estado_label = CTkLabel(nota_container, text=estado_text, width=20,
                                   text_color=estado_color,
                                   font=self.FUENTES["boton"])
            estado_label.pack(side="left", padx=5)
            
            obs_var = ctk.StringVar(value=obs_existente or "")
            entry_obs = CTkEntry(row, 
                                textvariable=obs_var,
                                placeholder_text="Sin observaciones",
                                font=self.FUENTES["pequeña"],
                                fg_color=COLORES["tarjeta"],
                                text_color=COLORES["texto"],
                                border_color=COLORES["borde"])
            entry_obs.pack(side="left", fill="x", expand=True, padx=10, pady=8)
            
            def guardar_al_salir(event, eid=est_id, nv=nota_var, ov=obs_var, 
                                el=estado_label, pm=puntos_max):
                self.guardar_nota_auto(eid, nv, ov, el, pm)
            
            entry_nota.bind("<FocusOut>", guardar_al_salir)
            entry_obs.bind("<FocusOut>", guardar_al_salir)
            entry_nota.bind("<Return>", guardar_al_salir)
            entry_obs.bind("<Return>", guardar_al_salir)
            
            self.entries_notas[est_id] = (nota_var, obs_var, estado_label)

    def mostrar_modal_estudiante(self, estudiante):
        est_id, nombre, grupo, email, carne = estudiante
        
        if not self.current_evaluacion:
            self.mostrar_modal_estudiante_simple(estudiante)
            return
        
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
        
        if not eval_info:
            self.mostrar_modal_estudiante_simple(estudiante)
            return
        
        eval_nombre = eval_info[1]
        puntos_max_eval = eval_info[2]
        
        criterios = self.db.get_criterios_rubrica(self.current_evaluacion)
        
        if not criterios:
            self.mostrar_modal_estudiante_simple(estudiante,
                mensaje_extra="\n\nEsta evaluación no tiene rúbrica definida.\nUse el botón 'Rúbrica' para crearla.")
            return
        
        altura_por_criterio = 80
        altura_minima = 500
        altura_maxima = 800
        altura_base = 350
        altura_calculada = min(max(altura_minima, altura_base + (len(criterios) * altura_por_criterio)), altura_maxima)
        
        modal = ctk.CTkToplevel(self)
        modal.title(f"Calificar: {nombre}")
        modal.geometry(f"600x{altura_calculada}")
        modal.transient(self)
        modal.grab_set()
        
        modal.update_idletasks()
        x = (modal.winfo_screenwidth() // 2) - (600 // 2)
        y = (modal.winfo_screenheight() // 2) - (altura_calculada // 2)
        modal.geometry(f"600x{altura_calculada}+{x}+{y}")
        
        main_frame = CTkFrame(modal, fg_color=COLORES["fondo"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        header_frame = CTkFrame(main_frame,
                               fg_color=COLORES["primario"],
                               corner_radius=8)
        header_frame.pack(fill="x", pady=(0, 10))
        
        CTkLabel(header_frame,
                text=nombre,
                font=self.FUENTES["subtitulo"],
                text_color="white").pack(pady=12)
        
        info_frame = CTkFrame(main_frame,
                             fg_color=COLORES["tarjeta"],
                             corner_radius=6)
        info_frame.pack(fill="x", pady=5)
        
        info_text = f"Grupo: {grupo}  |  Carné: {carne or 'N/A'}  |  Email: {email or 'N/A'}"
        
        CTkLabel(info_frame,
                text=info_text,
                font=self.FUENTES["pequeña"],
                text_color=COLORES["texto_secundario"]).pack(pady=8)
        
        title_frame = CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=10)
        
        CTkLabel(title_frame,
                text=eval_nombre,
                font=self.FUENTES["subtitulo"],
                text_color=COLORES["texto"]).pack(side="left", padx=5)
        CTkLabel(title_frame,
                text=f"(Máx: {puntos_max_eval} pts)",
                font=self.FUENTES["normal"],
                text_color=COLORES["texto_secundario"]).pack(side="left", padx=5)
        
        altura_scroll = max(200, altura_calculada - 300)
        
        scroll_rubrica = CTkScrollableFrame(main_frame,
                                           fg_color=COLORES["tarjeta"],
                                           height=altura_scroll,
                                           corner_radius=8)
        scroll_rubrica.pack(fill="both", expand=True, pady=5)
        
        calificaciones_previas = self.db.get_calificaciones_rubrica_estudiante(est_id, self.current_evaluacion)
        
        entries_criterios = {}
        
        for crit in calificaciones_previas:
            crit_id, nombre_criterio, puntos_max, puntos_obtenidos, obs = crit
            
            frame_crit = CTkFrame(scroll_rubrica,
                                 fg_color=COLORES["fondo"],
                                 corner_radius=6)
            frame_crit.pack(fill="x", pady=4, padx=2)
            
            header_crit = CTkFrame(frame_crit, fg_color="transparent")
            header_crit.pack(fill="x", padx=10, pady=(8, 4))
            
            CTkLabel(header_crit,
                    text=nombre_criterio,
                    font=self.FUENTES["boton"],
                    text_color=COLORES["texto"]).pack(side="left")
            CTkLabel(header_crit,
                    text=f"(máx: {puntos_max})",
                    font=self.FUENTES["pequeña"],
                    text_color=COLORES["texto_secundario"]).pack(side="left", padx=5)
            
            input_frame = CTkFrame(frame_crit, fg_color="transparent")
            input_frame.pack(fill="x", padx=10, pady=(0, 8))
            
            var_puntos = ctk.StringVar(value=str(puntos_obtenidos) if puntos_obtenidos > 0 else "")
            entry_puntos = CTkEntry(input_frame,
                                   width=70,
                                   height=28,
                                   textvariable=var_puntos,
                                   placeholder_text=f"0-{puntos_max}",
                                   font=self.FUENTES["normal"],
                                   fg_color=COLORES["tarjeta"],
                                   text_color=COLORES["texto"],
                                   border_color=COLORES["borde"])
            entry_puntos.pack(side="left", padx=2)
            
            CTkLabel(input_frame,
                    text="/",
                    font=self.FUENTES["normal"],
                    text_color=COLORES["texto_secundario"]).pack(side="left", padx=2)
            CTkLabel(input_frame,
                    text=f"{puntos_max}",
                    font=self.FUENTES["boton"],
                    text_color=COLORES["texto"]).pack(side="left", padx=2)
            
            var_obs = ctk.StringVar(value=obs or "")
            entry_obs = CTkEntry(input_frame,
                                placeholder_text="Observaciones...",
                                textvariable=var_obs,
                                width=280,
                                height=28,
                                font=self.FUENTES["pequeña"],
                                fg_color=COLORES["tarjeta"],
                                text_color=COLORES["texto"],
                                border_color=COLORES["borde"])
            entry_obs.pack(side="left", padx=10, fill="x", expand=True)
            
            entries_criterios[crit_id] = {
                'puntos': var_puntos,
                'obs': var_obs,
                'max': puntos_max,
                'nombre': nombre_criterio
            }
        
        bottom_frame = CTkFrame(main_frame,
                               fg_color=COLORES["tarjeta"],
                               corner_radius=8)
        bottom_frame.pack(fill="x", pady=10)
        
        lbl_total = CTkLabel(bottom_frame,
                            text=f"Total: 0 / {puntos_max_eval}",
                            font=self.FUENTES["subtitulo"],
                            text_color=COLORES["texto"])
        lbl_total.pack(pady=10)
        
        def calcular_total():
            total = 0
            for entries in entries_criterios.values():
                try:
                    puntos = float(entries['puntos'].get() or 0)
                    total += puntos
                except:
                    pass
            
            if total == puntos_max_eval:
                color = COLORES["exito"]
            elif total < puntos_max_eval:
                color = COLORES["alerta"]
            else:
                color = COLORES["peligro"]
            
            lbl_total.configure(text=f"Total: {total} / {puntos_max_eval}", text_color=color)
            return total
        
        calcular_total()
        
        for entries in entries_criterios.values():
            entries['puntos'].trace_add("write", lambda *args: calcular_total())
        
        btn_frame = CTkFrame(bottom_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        def aceptar_y_guardar():
            try:
                total = 0
                
                for crit_id, entries in entries_criterios.items():
                    puntos_str = entries['puntos'].get().strip()
                    puntos = float(puntos_str) if puntos_str else 0
                    obs = entries['obs'].get().strip()
                    
                    if puntos > entries['max']:
                        messagebox.showerror("Error",
                            f"'{entries['nombre']}': máximo {entries['max']} puntos")
                        return
                    
                    self.db.guardar_calificacion_rubrica(est_id, crit_id, puntos, obs)
                    total += puntos
                
                if total > puntos_max_eval:
                    messagebox.showerror("Error",
                        f"Total ({total}) excede el máximo ({puntos_max_eval})")
                    return
                
                self.db.guardar_nota(est_id, self.current_evaluacion, total, "Calificado por rúbrica")
                
                self.load_estudiantes_notas()
                self.actualizar_resumen()
                
                modal.destroy()
                
                self.status_label.configure(
                    text=f"Guardado: {nombre} = {total}/{puntos_max_eval} pts",
                    text_color=COLORES["exito"]
                )
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
        
        CTkButton(btn_frame,
                 text="GUARDAR",
                 command=aceptar_y_guardar,
                 fg_color=COLORES["exito"],
                 hover_color="#219A52",
                 height=40,
                 font=self.FUENTES["boton"]).pack(side="left", padx=5, fill="x", expand=True)
        
        CTkButton(btn_frame,
                 text="Cancelar",
                 command=modal.destroy,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 height=40,
                 font=self.FUENTES["boton"]).pack(side="left", padx=5, fill="x", expand=True)

    def mostrar_modal_estudiante_simple(self, estudiante, mensaje_extra=""):
        est_id, nombre, grupo, email, carne = estudiante
        
        modal = ctk.CTkToplevel(self)
        modal.title("Datos del Estudiante")
        modal.geometry("400x300")
        modal.transient(self)
        modal.grab_set()
        
        modal.update_idletasks()
        x = (modal.winfo_screenwidth() // 2) - (400 // 2)
        y = (modal.winfo_screenheight() // 2) - (300 // 2)
        modal.geometry(f"400x300+{x}+{y}")
        
        frame = CTkFrame(modal, fg_color=COLORES["fondo"])
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        CTkLabel(frame,
                text="INFORMACIÓN DEL ESTUDIANTE",
                font=self.FUENTES["subtitulo"],
                text_color=COLORES["texto"]).pack(pady=(15, 10))
        
        CTkLabel(frame,
                text=nombre,
                font=self.FUENTES["titulo"],
                text_color=COLORES["primario"]).pack()
        
        datos_frame = CTkFrame(frame,
                              fg_color=COLORES["tarjeta"],
                              corner_radius=8)
        datos_frame.pack(fill="x", padx=20, pady=15)
        
        CTkLabel(datos_frame,
                text=f"Grupo: {grupo}",
                font=self.FUENTES["normal"],
                text_color=COLORES["texto"]).pack(anchor="w", padx=15, pady=5)
        CTkLabel(datos_frame,
                text=f"Carné: {carne or 'No registrado'}",
                font=self.FUENTES["normal"],
                text_color=COLORES["texto"]).pack(anchor="w", padx=15, pady=5)
        CTkLabel(datos_frame,
                text=f"Email: {email or 'No registrado'}",
                font=self.FUENTES["normal"],
                text_color=COLORES["texto"]).pack(anchor="w", padx=15, pady=5)
        
        if mensaje_extra:
            CTkLabel(frame,
                    text=mensaje_extra,
                    font=self.FUENTES["pequeña"],
                    text_color=COLORES["alerta"]).pack(pady=10)
        
        CTkButton(frame,
                 text="Cerrar",
                 command=modal.destroy,
                 fg_color=COLORES["acento"],
                 hover_color="#2980B9",
                 height=35,
                 font=self.FUENTES["boton"]).pack(pady=15)

    def guardar_nota_auto(self, estudiante_id, nota_var, obs_var, estado_label, puntos_maximos=None):
        """Guarda nota automáticamente validando que no exceda el máximo de la evaluación"""
        try:
            puntos_str = nota_var.get().strip()
            
            if not puntos_str:
                estado_label.configure(text="-", text_color="gray")
                if hasattr(self, 'guardado_status_label') and self.guardado_status_label.winfo_exists():
                    self.guardado_status_label.configure(text="Estado: Sin cambios", text_color="gray")
                return
            
            puntos_ingresados = float(puntos_str)
            
            if puntos_maximos is None:
                evals = self.db.get_evaluaciones(self.current_curso)
                eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
                if not eval_info:
                    estado_label.configure(text="ERR", text_color="red")
                    self.status_label.configure(text="Error: Evaluación no encontrada", text_color="red")
                    return
                puntos_maximos = eval_info[2] 
            
            if puntos_ingresados < 0:
                estado_label.configure(text="ERR", text_color="red")
                self.status_label.configure(text="Error: No puede ser negativo", text_color="red")
                if hasattr(self, 'guardado_status_label') and self.guardado_status_label.winfo_exists():
                    self.guardado_status_label.configure(text="Estado: Error", text_color="red")
                return
                
            if puntos_ingresados > puntos_maximos:
                estado_label.configure(text="ERR", text_color="red")
                self.status_label.configure(text=f"Error: Máximo {puntos_maximos} puntos", text_color="red")
                if hasattr(self, 'guardado_status_label') and self.guardado_status_label.winfo_exists():
                    self.guardado_status_label.configure(text="Estado: Error - Excede máximo", text_color="red")
                return
            
            self.db.guardar_nota(estudiante_id, self.current_evaluacion, puntos_ingresados, obs_var.get())
            
            estado_label.configure(text="OK", text_color="green")
            self.status_label.configure(text=f"Guardado: {puntos_ingresados}/{puntos_maximos} pts", text_color="green")
            if hasattr(self, 'guardado_status_label') and self.guardado_status_label.winfo_exists():
                self.guardado_status_label.configure(text="Estado: Guardado", text_color="green")
            
            self.after(100, self.actualizar_resumen)
            
        except ValueError:
            estado_label.configure(text="ERR", text_color="red")
            self.status_label.configure(text="Error: Ingresa un número válido", text_color="red")
            if hasattr(self, 'guardado_status_label') and self.guardado_status_label.winfo_exists():
                self.guardado_status_label.configure(text="Estado: Error de formato", text_color="red")

    def refrescar_vista(self):
        if self.current_evaluacion:
            self.load_estudiantes_notas()
            self.status_label.configure(text="Vista actualizada")

    def setup_tab_notas(self):
        self.tab_notas.grid_columnconfigure(0, weight=1)
        self.tab_notas.grid_rowconfigure(1, weight=1)
        self.tab_notas.configure(fg_color=COLORES["tarjeta"])
        
        self.info_frame = CTkFrame(self.tab_notas, 
                                  fg_color=COLORES["fondo"],
                                  corner_radius=8)
        self.info_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        self.info_label = CTkLabel(self.info_frame, 
                                  text="Seleccione un curso y evaluación para comenzar", 
                                  font=self.FUENTES["subtitulo"],
                                  text_color=COLORES["texto"])
        self.info_label.pack(pady=12)
        
        self.scroll_frame = CTkScrollableFrame(self.tab_notas, 
                                              fg_color="transparent",
                                              corner_radius=8)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        self.btn_refrescar = CTkButton(self.tab_notas, 
                                      text="Actualizar Vista", 
                                      command=self.refrescar_vista, 
                                      height=40,
                                      fg_color=COLORES["secundario"],
                                      hover_color=COLORES["primario"],
                                      font=self.FUENTES["boton"])
        self.btn_refrescar.grid(row=2, column=0, pady=15)

    def setup_tab_config(self):
        self.tab_config.grid_columnconfigure(0, weight=1)
        self.tab_config.grid_rowconfigure(0, weight=1)
        self.tab_config.configure(fg_color=COLORES["tarjeta"])
        
        self.config_text = ctk.CTkTextbox(self.tab_config, 
                                         wrap="word", 
                                         font=self.FUENTES["normal"],
                                         fg_color=COLORES["fondo"],
                                         text_color=COLORES["texto"],
                                         border_color=COLORES["borde"],
                                         corner_radius=8)
        self.config_text.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.config_text.insert("0.0", "Seleccione un curso para ver su configuración...")
        self.config_text.configure(state="disabled")

    def setup_tab_resumen(self):
        self.tab_resumen.grid_columnconfigure(0, weight=1)
        self.tab_resumen.grid_rowconfigure(0, weight=1)
        self.tab_resumen.configure(fg_color=COLORES["tarjeta"])
        
        self.resumen_text = ctk.CTkTextbox(self.tab_resumen, 
                                          wrap="word", 
                                          font=self.FUENTES["normal"],
                                          fg_color=COLORES["fondo"],
                                          text_color=COLORES["texto"],
                                          border_color=COLORES["borde"],
                                          corner_radius=8)
        self.resumen_text.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.resumen_text.insert("0.0", "Seleccione un curso para ver estadísticas...")
        self.resumen_text.configure(state="disabled")

    def actualizar_config_curso(self):
        if not self.current_curso:
            return
        cursos = self.db.get_cursos()
        curso = next((c for c in cursos if c[0] == self.current_curso), None)
        evals = self.db.get_evaluaciones(self.current_curso)
        total_puntos = sum(e[2] for e in evals)
        
        texto = f"CONFIGURACIÓN DEL CURSO\n"
        texto += f"{'─' * 50}\n\n"
        texto += f"Nombre: {curso[1]}\n"
        texto += f"Descripción: {curso[2] or 'No especificada'}\n\n"
        texto += f"EVALUACIONES ({len(evals)} total, {total_puntos} puntos asignados)\n"
        texto += f"{'─' * 50}\n"
        
        if evals:
            for e in evals:
                texto += f"  {e[3]}. {e[1]} — {e[2]} puntos\n"
            if total_puntos != 100:
                texto += f"\n⚠ Advertencia: El total es {total_puntos} puntos (debería ser 100)\n"
        else:
            texto += "  No hay evaluaciones configuradas\n"
        
        estudiantes = self.db.get_estudiantes(self.current_curso)
        texto += f"\n\nESTUDIANTES: {len(estudiantes)}\n"
        texto += f"{'─' * 50}\n"
        
        grupos = {}
        for e in estudiantes:
            grupos[e[2]] = grupos.get(e[2], 0) + 1
        for g, count in sorted(grupos.items()):
            texto += f"  Grupo {g}: {count} estudiantes\n"
        
        self.config_text.configure(state="normal")
        self.config_text.delete("0.0", "end")
        self.config_text.insert("0.0", texto)
        self.config_text.configure(state="disabled")
        
    def agregar_tooltip(self, widget, texto):
        """Agrega un tooltip que aparece al pasar el mouse"""
        tooltip = None
        
        def mostrar_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
            
            tooltip = CTkToplevel(self)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = CTkLabel(tooltip, text=texto, 
                           font=ctk.CTkFont(size=10),
                           fg_color="gray20", 
                           corner_radius=6,
                           padx=10, pady=5)
            label.pack()
        
        def ocultar_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        widget.bind("<Enter>", mostrar_tooltip)
        widget.bind("<Leave>", ocultar_tooltip)

    def actualizar_resumen(self):
        if not self.current_curso:
            return
        cursos = self.db.get_cursos()
        curso = next((c for c in cursos if c[0] == self.current_curso), None)
        evals = self.db.get_evaluaciones(self.current_curso)
        estudiantes = self.db.get_estudiantes(self.current_curso)
        
        texto = f"RESUMEN: {curso[1]}\n"
        texto += f"{'─' * 50}\n\n"
        
        if estudiantes and evals:
            promedios = []
            for est in estudiantes:
                prom, _ = self.db.calcular_promedio(est[0], self.current_curso)
                promedios.append(prom)
            
            texto += f"PROMEDIO GENERAL: {statistics.mean(promedios):.2f} / 100\n"
            texto += f"Nota máxima: {max(promedios):.2f}\n"
            texto += f"Nota mínima: {min(promedios):.2f}\n"
            texto += f"Mediana: {statistics.median(promedios):.2f}\n"
            texto += f"Desviación estándar: {statistics.stdev(promedios) if len(promedios) > 1 else 0:.2f}\n\n"
            
            rangos = {'0-59': 0, '60-69': 0, '70-79': 0, '80-89': 0, '90-100': 0}
            for p in promedios:
                if p < 60: rangos['0-59'] += 1
                elif p < 70: rangos['60-69'] += 1
                elif p < 80: rangos['70-79'] += 1
                elif p < 90: rangos['80-89'] += 1
                else: rangos['90-100'] += 1
            
            texto += "DISTRIBUCIÓN DE NOTAS\n"
            texto += f"{'─' * 50}\n"
            for r, c in rangos.items():
                porcentaje = (c / len(promedios) * 100) if promedios else 0
                barra = "█" * int(porcentaje / 5)
                texto += f"{r:>6}: {barra:<20} {c:>3} est. ({porcentaje:.1f}%)\n"
        else:
            texto += "Agregue evaluaciones y estudiantes para ver estadísticas.\n"
        
        self.resumen_text.configure(state="normal")
        self.resumen_text.delete("0.0", "end")
        self.resumen_text.insert("0.0", texto)
        self.resumen_text.configure(state="disabled")

    def actualizar_info_curso(self):
        if self.current_curso:
            for nombre, cid in self.cursos_data.items():
                if cid == self.current_curso:
                    self.info_label.configure(text=f"Curso: {nombre}")
                    return
        else:
            self.info_label.configure(text="Selecciona un curso y evaluacion para comenzar")

    def limpiar_interfaz(self):
        self.info_label.configure(text="Selecciona un curso y evaluacion para comenzar")
        self.limpiar_tab_notas()
        self.config_text.configure(state="normal")
        self.config_text.delete("0.0", "end")
        self.config_text.insert("0.0", "Selecciona un curso...")
        self.config_text.configure(state="disabled")
        self.resumen_text.configure(state="normal")
        self.resumen_text.delete("0.0", "end")
        self.resumen_text.insert("0.0", "Selecciona un curso...")
        self.resumen_text.configure(state="disabled")

    def limpiar_tab_notas(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        CTkLabel(self.scroll_frame, text="Selecciona un curso y una evaluacion para ver los estudiantes", font=ctk.CTkFont(size=12)).pack(pady=20)

    def exportar_excel(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        nombre_archivo = "curso"
        for nombre, cid in self.cursos_data.items():
            if cid == self.current_curso:
                nombre_archivo = nombre.replace(" ", "_")
                break
        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")], initialfile=f"notas_{nombre_archivo}.xlsx")
        if filepath:
            try:
                self.db.exportar_a_excel(self.current_curso, filepath)
                self.status_label.configure(text="Exportado")
                messagebox.showinfo("Exito", f"Archivo guardado:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar:\n{str(e)}")

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.sidebar = CTkFrame(self, width=320, corner_radius=0, 
                               fg_color=COLORES["primario"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar.grid_propagate(False)
        
        self.sidebar_scroll = CTkScrollableFrame(self.sidebar, width=300, 
                                                fg_color="transparent",
                                                scrollbar_button_color=COLORES["secundario"])
        self.sidebar_scroll.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        self.title_label = CTkLabel(self.sidebar_scroll, 
                                   text="GESTOR DE EVALUACIONES",
                                   font=self.FUENTES["titulo"],
                                   text_color="white")
        self.title_label.pack(pady=(0, 20))
        
        separador = CTkFrame(self.sidebar_scroll, height=2, fg_color=COLORES["acento"])
        separador.pack(fill="x", pady=(0, 15))
        
        self.cursos_frame = CTkFrame(self.sidebar_scroll, fg_color=COLORES["secundario"],
                                    corner_radius=8)
        self.cursos_frame.pack(fill="x", pady=8)
        
        header_cursos = CTkFrame(self.cursos_frame, fg_color="transparent")
        header_cursos.pack(fill="x", padx=12, pady=(10, 5))
        
        CTkLabel(header_cursos, text="CURSOS", 
                font=self.FUENTES["subtitulo"],
                text_color="white").pack(side="left")
        
        CTkLabel(header_cursos, text=str(len(self.cursos_data)) if hasattr(self, 'cursos_data') else "0",
                font=self.FUENTES["pequeña"],
                text_color=COLORES["texto_secundario"]).pack(side="right")
        
        self.cursos_scroll = CTkScrollableFrame(self.cursos_frame, height=120,
                                               fg_color=COLORES["primario"],
                                               corner_radius=6)
        self.cursos_scroll.pack(fill="x", padx=10, pady=5)
        
        btn_frame = CTkFrame(self.cursos_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        CTkButton(btn_frame, text="Nuevo", width=70, 
                 command=self.crear_curso,
                 fg_color=COLORES["acento"],
                 hover_color="#2980B9",
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="Editar", width=70, 
                 command=self.editar_curso,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="Eliminar", width=60, 
                 command=self.eliminar_curso, 
                 fg_color=COLORES["peligro"],
                 hover_color="#A93226",
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", padx=2)
        
        self.evals_frame = CTkFrame(self.sidebar_scroll, fg_color=COLORES["secundario"],
                                   corner_radius=8)
        self.evals_frame.pack(fill="x", pady=8)
        
        header_evals = CTkFrame(self.evals_frame, fg_color="transparent")
        header_evals.pack(fill="x", padx=12, pady=(10, 5))
        
        CTkLabel(header_evals, text="EVALUACIONES", 
                font=self.FUENTES["subtitulo"],
                text_color="white").pack(side="left")
        
        self.evals_scroll = CTkScrollableFrame(self.evals_frame, height=120,
                                              fg_color=COLORES["primario"],
                                              corner_radius=6)
        self.evals_scroll.pack(fill="x", padx=10, pady=5)
        
        btn_frame = CTkFrame(self.evals_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        CTkButton(btn_frame, text="Nueva", width=55, 
                 command=self.agregar_evaluacion,
                 fg_color=COLORES["acento"],
                 hover_color="#2980B9",
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="Editar", width=55, 
                 command=self.editar_evaluacion,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="Rúbrica", width=55, 
                 command=self.editar_rubrica, 
                 fg_color="#8E44AD",
                 hover_color="#7D3C98",
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="X", width=40, 
                 command=self.eliminar_evaluacion, 
                 fg_color=COLORES["alerta"],
                 hover_color="#D35400",
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", padx=2)
        
        self.est_frame = CTkFrame(self.sidebar_scroll, fg_color=COLORES["secundario"],
                                 corner_radius=8)
        self.est_frame.pack(fill="x", pady=8)
        
        CTkLabel(self.est_frame, text="ESTUDIANTES", 
                font=self.FUENTES["subtitulo"],
                text_color="white").pack(pady=(10, 5))
        
        CTkButton(self.est_frame, text="Agregar Estudiante", 
                 command=self.agregar_estudiante,
                 fg_color=COLORES["acento"],
                 hover_color="#2980B9",
                 font=self.FUENTES["boton"],
                 height=35).pack(pady=3, fill="x", padx=10)
        CTkButton(self.est_frame, text="Agregar Varios", 
                 command=self.agregar_varios_estudiantes,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"],
                 height=32).pack(pady=2, fill="x", padx=10)
        
        btn_frame = CTkFrame(self.est_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        CTkButton(btn_frame, text="Editar", 
                 command=self.editar_estudiante,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", fill="x", expand=True, padx=2)
        CTkButton(btn_frame, text="Eliminar", 
                 command=self.eliminar_estudiante, 
                 fg_color=COLORES["peligro"],
                 hover_color="#A93226",
                 font=self.FUENTES["boton"],
                 height=32).pack(side="left", fill="x", expand=True, padx=2)
        
        self.tools_frame = CTkFrame(self.sidebar_scroll, fg_color=COLORES["secundario"],
                                   corner_radius=8)
        self.tools_frame.pack(fill="x", pady=8)
        
        CTkLabel(self.tools_frame, text="HERRAMIENTAS", 
                font=self.FUENTES["subtitulo"],
                text_color="white").pack(pady=(10, 5))
        
        CTkButton(self.tools_frame, text="Exportar a Excel", 
                 command=self.exportar_excel,
                 fg_color="#16A085",
                 hover_color="#138D75",
                 font=self.FUENTES["boton"],
                 height=35).pack(pady=3, fill="x", padx=10)
        CTkButton(self.tools_frame, text="Sincronizar Datos", 
                 command=self.sincronizar_manual, 
                 fg_color=COLORES["exito"],
                 hover_color="#219A52",
                 font=self.FUENTES["boton"],
                 height=35).pack(pady=3, fill="x", padx=10)
        
        self.status_frame = CTkFrame(self.sidebar_scroll, fg_color="transparent")
        self.status_frame.pack(fill="x", pady=15)
        
        self.status_label = CTkLabel(self.status_frame, 
                                    text="Sistema Listo",
                                    font=self.FUENTES["pequeña"],
                                    text_color=COLORES["texto_secundario"])
        self.status_label.pack()
        
        self.main_frame = CTkFrame(self, fg_color=COLORES["fondo"])
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        self.tabview = CTkTabview(self.main_frame,
                                 fg_color=COLORES["tarjeta"],
                                 segmented_button_fg_color=COLORES["secundario"],
                                 segmented_button_selected_color=COLORES["acento"],
                                 segmented_button_selected_hover_color="#2980B9",
                                 segmented_button_unselected_color=COLORES["secundario"],
                                 segmented_button_unselected_hover_color=COLORES["primario"],
                                 text_color="white")
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        self.tab_notas = self.tabview.add("Registro de Notas")
        self.tab_clases = self.tabview.add("Control de Clases")
        self.tab_config = self.tabview.add("Configuración")
        self.tab_resumen = self.tabview.add("Resumen")
        
        self.setup_tab_notas()
        self.setup_tab_clases()
        self.setup_tab_config()
        self.setup_tab_resumen()

    def setup_tab_clases(self):
        self.tab_clases.grid_columnconfigure(0, weight=3)
        self.tab_clases.grid_columnconfigure(1, weight=1)
        self.tab_clases.grid_rowconfigure(0, weight=1)
        self.tab_clases.configure(fg_color=COLORES["tarjeta"])
        
        scroll_principal = CTkScrollableFrame(self.tab_clases,
                                             fg_color="transparent")
        scroll_principal.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        scroll_principal.grid_columnconfigure(0, weight=1)
        
        self.clases_content_frame = CTkFrame(scroll_principal,
                                            fg_color=COLORES["fondo"],
                                            corner_radius=10)
        self.clases_content_frame.pack(fill="x", padx=5, pady=5)
        self.clases_content_frame.grid_columnconfigure(0, weight=1)
        
        toolbar = CTkFrame(self.clases_content_frame, 
                          fg_color=COLORES["primario"],
                          corner_radius=6)
        toolbar.pack(fill="x", padx=10, pady=(10, 20))
        
        fecha_container = CTkFrame(toolbar, fg_color="transparent")
        fecha_container.pack(side="left", padx=15, pady=10)
        
        CTkLabel(fecha_container, text="FECHA:", 
                font=self.FUENTES["boton"],
                text_color="white").pack(side="left", padx=(0, 10))
        
        self.fecha_clase_var = ctk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        
        self.btn_fecha_clase = CTkButton(fecha_container, 
                                        text=self.fecha_clase_var.get(),
                                        width=100,
                                        height=30,
                                        command=self.abrir_selector_fecha,
                                        fg_color=COLORES["acento"],
                                        hover_color="#2980B9",
                                        font=self.FUENTES["boton"])
        self.btn_fecha_clase.pack(side="left")
        
        def poner_fecha_hoy():
            hoy = date.today().strftime("%d/%m/%Y")
            self.fecha_clase_var.set(hoy)
            self.btn_fecha_clase.configure(text=hoy)
        
        CTkButton(fecha_container, text="Hoy", width=50, height=30,
                 command=poner_fecha_hoy,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"]).pack(side="left", padx=8)
        
        grupo_container = CTkFrame(toolbar, fg_color="transparent")
        grupo_container.pack(side="left", padx=15, pady=10)
        
        CTkLabel(grupo_container, text="GRUPO:", 
                font=self.FUENTES["boton"],
                text_color="white").pack(side="left", padx=(0, 10))
        
        self.grupo_clase_var = ctk.StringVar(value="1")
        def cambiar_grupo(nuevo_grupo):
            self.lbl_info_grupo_clase.configure(text=f"Clases del Grupo {nuevo_grupo}")
            self.cargar_lista_clases()

        self.combo_grupo_clase = CTkOptionMenu(grupo_container, 
                                              values=["1", "2", "3", "4", "5"],
                                              variable=self.grupo_clase_var,
                                              width=70,
                                              command=cambiar_grupo,
                                              fg_color=COLORES["acento"],
                                              button_color="#2980B9",
                                              text_color="white",
                                              font=self.FUENTES["boton"])
        self.combo_grupo_clase.pack(side="left")
        
        self.lbl_info_grupo_clase = CTkLabel(toolbar, 
                                            text="Clases del Grupo 1",
                                            font=self.FUENTES["normal"],
                                            text_color=COLORES["texto_secundario"])
        self.lbl_info_grupo_clase.pack(side="right", padx=15)
        
        CTkLabel(self.clases_content_frame, text="TÍTULO DE LA CLASE", 
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(pady=(15, 5), padx=15, anchor="w")
        
        self.entry_encabezado_clase = CTkEntry(self.clases_content_frame, 
                                               placeholder_text="Ej: Introducción al curso - Conceptos fundamentales",
                                               height=40,
                                               font=self.FUENTES["normal"],
                                               fg_color=COLORES["tarjeta"],
                                               text_color=COLORES["texto"],
                                               border_color=COLORES["borde"])
        self.entry_encabezado_clase.pack(fill="x", padx=15, pady=5)
        
        CTkLabel(self.clases_content_frame, text="TÓPICOS", 
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(pady=(15, 5), padx=15, anchor="w")
        
        self.entry_topicos = CTkEntry(self.clases_content_frame, 
                                     placeholder_text="1. Presentación, 2. Objetivos, 3. Metodología...",
                                     height=35,
                                     font=self.FUENTES["normal"],
                                     fg_color=COLORES["tarjeta"],
                                     text_color=COLORES["texto"],
                                     border_color=COLORES["borde"])
        self.entry_topicos.pack(fill="x", padx=15, pady=5)
        
        CTkLabel(self.clases_content_frame, text="LECTURAS Y RECURSOS", 
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(pady=(15, 5), padx=15, anchor="w")
        
        self.frame_links = CTkFrame(self.clases_content_frame,
                                   fg_color=COLORES["tarjeta"],
                                   corner_radius=6)
        self.frame_links.pack(fill="x", padx=15, pady=5)
        
        self.links_entries = []
        
        CTkButton(self.clases_content_frame, text="+ Agregar Recurso", 
                 command=self.agregar_campo_link,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"],
                 height=32).pack(pady=5, padx=15, anchor="w")
        
        self.agregar_campo_link()
        
        CTkLabel(self.clases_content_frame, text="DESARROLLO DE LA CLASE", 
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(pady=(15, 5), padx=15, anchor="w")
        
        toolbar_frame = CTkFrame(self.clases_content_frame, 
                                fg_color=COLORES["secundario"],
                                corner_radius=4)
        toolbar_frame.pack(fill="x", padx=15, pady=2)
        
        CTkButton(toolbar_frame, text="B", width=40, 
                 command=lambda: self.aplicar_formato_texto("bold"),
                 fg_color="transparent",
                 font=ctk.CTkFont(family="Helvetica", size=12, weight="bold")).pack(side="left", padx=2, pady=4)
        CTkButton(toolbar_frame, text="I", width=40, 
                 command=lambda: self.aplicar_formato_texto("italic"),
                 fg_color="transparent",
                 font=ctk.CTkFont(family="Helvetica", size=12, slant="italic")).pack(side="left", padx=2, pady=4)
        CTkButton(toolbar_frame, text="U", width=40, 
                 command=lambda: self.aplicar_formato_texto("underline"),
                 fg_color="transparent",
                 font=ctk.CTkFont(family="Helvetica", size=12, underline=True)).pack(side="left", padx=2, pady=4)
        
        text_container = CTkFrame(self.clases_content_frame,
                                 fg_color=COLORES["tarjeta"],
                                 corner_radius=6)
        text_container.pack(fill="x", padx=15, pady=5)
        
        self.texto_clase = tk.Text(text_container, wrap="word", 
                                  font=("Consolas", 11), 
                                  height=12,
                                  bg="#FFFFFF",
                                  fg=COLORES["texto"],
                                  insertbackground=COLORES["primario"],
                                  relief="flat",
                                  borderwidth=0,
                                  padx=10,
                                  pady=10)
        self.texto_clase.pack(fill="both", expand=True, padx=2, pady=2)
        
        CTkLabel(self.clases_content_frame, text="OBSERVACIONES", 
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(pady=(15, 5), padx=15, anchor="w")
        
        self.entry_observaciones = CTkEntry(self.clases_content_frame, 
                                           placeholder_text="Recordatorios, tareas pendientes, materiales necesarios...",
                                           height=50,
                                           font=self.FUENTES["normal"],
                                           fg_color=COLORES["tarjeta"],
                                           text_color=COLORES["texto"],
                                           border_color=COLORES["borde"])
        self.entry_observaciones.pack(fill="x", padx=15, pady=5)
        
        btn_frame = CTkFrame(self.clases_content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=20)
        
        CTkButton(btn_frame, text="Guardar Clase", 
                 command=self.guardar_clase,
                 fg_color=COLORES["exito"],
                 hover_color="#219A52",
                 height=45,
                 font=self.FUENTES["boton"]).pack(side="left", padx=5, fill="x", expand=True)
        CTkButton(btn_frame, text="Exportar PDF", 
                 command=self.exportar_clase_pdf,
                 fg_color=COLORES["acento"],
                 hover_color="#2980B9",
                 height=45,
                 font=self.FUENTES["boton"]).pack(side="left", padx=5, fill="x", expand=True)
        CTkButton(btn_frame, text="Exportar Todas", 
                 command=self.exportar_todas_clases_pdf,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 height=45,
                 font=self.FUENTES["boton"]).pack(side="left", padx=5, fill="x", expand=True)
        
        self.clases_tools_frame = CTkFrame(self.tab_clases,
                                          fg_color=COLORES["fondo"],
                                          corner_radius=10)
        self.clases_tools_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        
        CTkLabel(self.clases_tools_frame, text="CLASES GUARDADAS", 
                font=self.FUENTES["subtitulo"],
                text_color=COLORES["texto"]).pack(pady=(15, 10), padx=10)
        
        self.combo_clases_guardadas = CTkOptionMenu(self.clases_tools_frame, 
                                                    values=["-- Nueva Clase --"],
                                                    command=self.cargar_clase_guardada,
                                                    fg_color=COLORES["secundario"],
                                                    button_color=COLORES["primario"],
                                                    font=self.FUENTES["normal"])
        self.combo_clases_guardadas.pack(fill="x", padx=10, pady=5)
        
        CTkButton(self.clases_tools_frame, text="Actualizar Lista", 
                 command=self.cargar_lista_clases,
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"]).pack(pady=5, padx=10, fill="x")
        
        CTkButton(self.clases_tools_frame, text="Eliminar Seleccionada", 
                 command=self.eliminar_clase_guardada,
                 fg_color=COLORES["peligro"],
                 hover_color="#A93226",
                 font=self.FUENTES["boton"]).pack(pady=5, padx=10, fill="x")
        
        separador = CTkFrame(self.clases_tools_frame, height=2, 
                            fg_color=COLORES["borde"])
        separador.pack(fill="x", padx=10, pady=15)
        
        CTkLabel(self.clases_tools_frame, text="CONTROL DE ASISTENCIA", 
                font=self.FUENTES["subtitulo"],
                text_color=COLORES["texto"]).pack(pady=5, padx=10)
        
        CTkButton(self.clases_tools_frame, text="Registrar Asistencia", 
                 command=self.abrir_asistencia,
                 height=50,
                 fg_color=COLORES["alerta"],
                 hover_color="#D35400",
                 font=self.FUENTES["boton"]).pack(pady=10, padx=10, fill="x")
        
        self.status_clases_label = CTkLabel(self.clases_tools_frame, 
                                           text="Sistema listo",
                                           font=self.FUENTES["pequeña"],
                                           text_color=COLORES["texto_secundario"])
        self.status_clases_label.pack(pady=20)
        
        self.entry_encabezado_clase.bind("<FocusOut>", lambda e: self.guardar_clase_auto())
        self.entry_topicos.bind("<FocusOut>", lambda e: self.guardar_clase_auto())
        self.entry_observaciones.bind("<FocusOut>", lambda e: self.guardar_clase_auto())
        self.texto_clase.bind("<FocusOut>", lambda e: self.guardar_clase_auto())

    def get_grupo_clase_actual(self):
        """Obtiene el número de grupo actualmente seleccionado en Control de Clases"""
        try:
            return int(self.grupo_clase_var.get())
        except (ValueError, AttributeError):
            return 1  

    def agregar_campo_link(self):
        frame_link = CTkFrame(self.frame_links,
                             fg_color=COLORES["fondo"],
                             corner_radius=4)
        frame_link.pack(fill="x", pady=3)
        
        entry_nombre = CTkEntry(frame_link, 
                               placeholder_text="Nombre del documento",
                               width=180,
                               font=self.FUENTES["pequeña"],
                               fg_color=COLORES["tarjeta"],
                               text_color=COLORES["texto"],
                               border_color=COLORES["borde"])
        
        entry_url = CTkEntry(frame_link, 
                            placeholder_text="https://...",
                            width=250,
                            font=self.FUENTES["pequeña"],
                            fg_color=COLORES["tarjeta"],
                            text_color=COLORES["texto"],
                            border_color=COLORES["borde"])
        entry_url.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        btn_abrir = CTkButton(frame_link, 
                             text="Abrir", 
                             width=60,
                             command=lambda: self.abrir_link(entry_url.get()),
                             fg_color=COLORES["acento"],
                             hover_color="#2980B9",
                             font=self.FUENTES["pequeña"],
                             height=28)
        btn_abrir.pack(side="left", padx=2, pady=5)
        
        btn_eliminar = CTkButton(frame_link, 
                                text="X", 
                                width=30,
                                command=lambda: frame_link.destroy(),
                                fg_color=COLORES["peligro"],
                                hover_color="#A93226",
                                font=self.FUENTES["pequeña"],
                                height=28)
        btn_eliminar.pack(side="left", padx=5, pady=5)
        
        self.links_entries.append((entry_nombre, entry_url))

    def abrir_link(self, url):
        import webbrowser
        if url and url.startswith("http"):
            webbrowser.open(url)
        else:
            messagebox.showwarning("URL invalida", "Ingresa una URL valida que empiece con http:// o https://")

    def aplicar_formato_texto(self, tipo):
        """Aplica formato de negrita, cursiva o subrayado al texto seleccionado"""
        try:
            if self.texto_clase.tag_ranges("sel"):
                inicio = self.texto_clase.index("sel.first")
                fin = self.texto_clase.index("sel.last")
                
                if tipo == "bold":
                    self.texto_clase.tag_configure("bold", font=("Segoe UI", 12, "bold"))
                    if "bold" in self.texto_clase.tag_names(inicio):
                        self.texto_clase.tag_remove("bold", inicio, fin)
                    else:
                        self.texto_clase.tag_add("bold", inicio, fin)
                        
                elif tipo == "italic":
                    self.texto_clase.tag_configure("italic", font=("Segoe UI", 12, "italic"))
                    if "italic" in self.texto_clase.tag_names(inicio):
                        self.texto_clase.tag_remove("italic", inicio, fin)
                    else:
                        self.texto_clase.tag_add("italic", inicio, fin)
                        
                elif tipo == "underline":
                    self.texto_clase.tag_configure("underline", underline=True)
                    if "underline" in self.texto_clase.tag_names(inicio):
                        self.texto_clase.tag_remove("underline", inicio, fin)
                    else:
                        self.texto_clase.tag_add("underline", inicio, fin)
                        
        except tk.TclError:
            pass

    def guardar_clase_auto(self):
        if hasattr(self, 'clase_actual_id') and self.clase_actual_id:
            self.guardar_clase(silencioso=True)

    def guardar_clase(self, silencioso=False):
        """Guarda la clase actual en la base de datos SQLite"""
        if not self.current_curso:
            if not silencioso:
                messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        fecha_clase = self.fecha_clase_var.get()
        grupo_clase = self.get_grupo_clase_actual()
        
        encabezado = self.entry_encabezado_clase.get().strip()
        topicos = self.entry_topicos.get().strip()
        observaciones = self.entry_observaciones.get().strip()
        contenido = self.texto_clase.get("1.0", "end").strip()
        
        links = []
        for nombre_entry, url_entry in self.links_entries:
            try:
                if nombre_entry.winfo_exists() and url_entry.winfo_exists():
                    nombre = nombre_entry.get().strip()
                    url = url_entry.get().strip()
                    if nombre or url:
                        links.append({"nombre": nombre, "url": url})
            except:
                pass
        
        if not encabezado:
            from datetime import datetime
            encabezado = f"Clase del {datetime.now().strftime('%d/%m/%Y')}"
            self.entry_encabezado_clase.delete(0, "end")
            self.entry_encabezado_clase.insert(0, encabezado)
        
        es_nueva = not hasattr(self, 'clase_actual_id') or not self.clase_actual_id
        
        try:
            if es_nueva:
                clase_id, error = self.db.crear_clase(
                    self.current_curso, 
                    encabezado, 
                    topicos, 
                    contenido, 
                    observaciones,
                    fecha_clase,
                    grupo_clase
                )
                if error:
                    raise Exception(error)
                self.clase_actual_id = clase_id
            else:
                success, error = self.db.actualizar_clase(
                    self.clase_actual_id,
                    encabezado=encabezado,
                    grupo=grupo_clase,
                    topicos=topicos,
                    contenido=contenido,
                    observaciones=observaciones,
                    fecha_clase=fecha_clase
                )
                if not success:
                    raise Exception(error)
                self.db.eliminar_links_clase(self.clase_actual_id)
            
            if self.clase_actual_id and links:
                for link in links:
                    self.db.agregar_link_clase(self.clase_actual_id, link["nombre"], link["url"])
            
            if not silencioso:
                messagebox.showinfo("Éxito", f"Clase guardada correctamente:\n{encabezado[:50]}")
                self.status_clases_label.configure(text=f"Guardado: {encabezado[:30]}...")
                self.cargar_lista_clases()
                
        except Exception as e:
            if not silencioso:
                messagebox.showerror("Error", f"No se pudo guardar la clase:\n{str(e)}")

    def cargar_lista_clases(self):
        """Carga la lista de clases desde la base de datos"""
        if not self.current_curso:
            valores = ["-- Nueva Clase --"]
            self.clases_dict = {"-- Nueva Clase --": None}
            if hasattr(self, 'combo_clases_guardadas') and self.combo_clases_guardadas.winfo_exists():
                self.combo_clases_guardadas.configure(values=valores)
                self.combo_clases_guardadas.set("-- Nueva Clase --")
            return
        
        grupo_actual = self.get_grupo_clase_actual()
        clases_db = self.db.get_clases(self.current_curso, grupo=grupo_actual)
        
        valores = ["-- Nueva Clase --"]
        self.clases_dict = {"-- Nueva Clase --": None}
        
        for clase in clases_db:
            clase_id = clase[0]
            grupo = clase[1]
            encabezado = clase[2]
            fecha_clase = clase[6]
            
            display = ""
            if fecha_clase:
                display += f"[{fecha_clase}] "
            display += encabezado[:35]
            
            if len(display) > 50:
                display = display[:50] + "..."
            
            valores.append(display)
            self.clases_dict[display] = clase_id
        
        if hasattr(self, 'combo_clases_guardadas') and self.combo_clases_guardadas.winfo_exists():
            self.combo_clases_guardadas.configure(values=valores)
            self.combo_clases_guardadas.set("-- Nueva Clase --")

    def cargar_clase_guardada(self, seleccion):
        """Carga una clase guardada desde la base de datos"""
        if seleccion == "-- Nueva Clase --":
            self.limpiar_campos_clase()
            self.clase_actual_id = None
            return
                
        clase_id = self.clases_dict.get(seleccion)
        if not clase_id:
            return
        
        clase_data = self.db.get_clase_por_id(clase_id)
        
        if not clase_data:
            messagebox.showerror("Error", "No se pudo cargar la clase")
            return
        
        self.clase_actual_id = clase_id
        
        try:
            grupo_guardado = clase_data.get("grupo", 1)
            self.grupo_clase_var.set(str(grupo_guardado))
            self.lbl_info_grupo_clase.configure(text=f"Clases para Grupo {grupo_guardado}")
            
            self.entry_encabezado_clase.delete(0, "end")
            self.entry_encabezado_clase.insert(0, clase_data.get("encabezado", ""))

            fecha_guardada = clase_data.get("fecha_clase")
            if fecha_guardada:
                self.fecha_clase_var.set(fecha_guardada)
                self.btn_fecha_clase.configure(text=fecha_guardada)
            else:
                hoy = date.today().strftime("%d/%m/%Y")
                self.fecha_clase_var.set(hoy)
                self.btn_fecha_clase.configure(text=hoy)

            self.entry_encabezado_clase.delete(0, "end")
            self.entry_encabezado_clase.insert(0, clase_data.get("encabezado", ""))
            
            self.entry_topicos.delete(0, "end")
            self.entry_topicos.insert(0, clase_data.get("topicos", ""))
            
            self.entry_observaciones.delete(0, "end")
            self.entry_observaciones.insert(0, clase_data.get("observaciones", ""))
            
            self.texto_clase.delete("1.0", "end")
            self.texto_clase.insert("1.0", clase_data.get("contenido", ""))
            
            for widget in self.frame_links.winfo_children():
                widget.destroy()
            self.links_entries = []
            
            for link in clase_data.get("links", []):
                self.agregar_campo_link()
                if self.links_entries:
                    self.links_entries[-1][0].insert(0, link.get("nombre", ""))
                    self.links_entries[-1][1].insert(0, link.get("url", ""))
            
            self.status_clases_label.configure(text=f"Cargada: {clase_data.get('encabezado', '')[:30]}...")
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar la clase: {str(e)}")

    def eliminar_clase_guardada(self):
        """Elimina la clase seleccionada del combo de clases guardadas"""
        seleccion = self.combo_clases_guardadas.get()
        
        if seleccion == "-- Nueva Clase --" or not seleccion:
            messagebox.showwarning("Advertencia", "Selecciona una clase guardada para eliminar")
            return
        
        clase_id = self.clases_dict.get(seleccion)
        if not clase_id:
            messagebox.showerror("Error", "No se encontró el ID de la clase")
            return
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar permanentemente la clase '{seleccion}'?\n\nEsta acción no se puede deshacer."):
            try:
                success, error = self.db.eliminar_clase(clase_id)
                if success:
                    messagebox.showinfo("Éxito", "Clase eliminada correctamente")
                    self.status_clases_label.configure(text="Clase eliminada")
                    self.limpiar_campos_clase()
                    self.cargar_lista_clases()
                else:
                    messagebox.showerror("Error", f"No se pudo eliminar la clase:\n{error}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al eliminar: {str(e)}")

    def limpiar_campos_clase(self):
        """Limpia todos los campos de la clase para crear una nueva"""
        self.entry_encabezado_clase.delete(0, "end")
        self.entry_topicos.delete(0, "end")
        self.entry_observaciones.delete(0, "end")
        self.texto_clase.delete("1.0", "end")

        hoy = date.today().strftime("%d/%m/%Y")
        self.fecha_clase_var.set(hoy)
        self.btn_fecha_clase.configure(text=hoy)

        self.grupo_clase_var.set("1")
        self.lbl_info_grupo_clase.configure(text="Clases para Grupo 1")
        
        for widget in self.frame_links.winfo_children():
            widget.destroy()
        self.links_entries = []
        self.agregar_campo_link()
        
        self.status_clases_label.configure(text="Nueva clase")
        self.clase_actual_id = None

    def abrir_selector_fecha(self):
        """Abre un calendario emergente para seleccionar la fecha"""
        popup = CTkToplevel(self)
        popup.title("Seleccionar Fecha")
        popup.geometry("300x300")
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (300 // 2)
        y = (popup.winfo_screenheight() // 2) - (300 // 2)
        popup.geometry(f"300x300+{x}+{y}")
        
        CTkLabel(popup, text="Selecciona la fecha:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        from datetime import datetime
        try:
            fecha_str = self.fecha_clase_var.get()
            fecha_actual = datetime.strptime(fecha_str, "%d/%m/%Y")
            year, month, day = fecha_actual.year, fecha_actual.month, fecha_actual.day
        except:
            hoy = date.today()
            year, month, day = hoy.year, hoy.month, hoy.day
        
        cal = Calendar(popup, selectmode='day', 
                    year=year, month=month, day=day,
                    locale='es_ES', font="Arial 9",
                    background='blue', foreground='white',
                    selectbackground='red', selectforeground='yellow')
        cal.pack(pady=10)
        
        def seleccionar():
            self.fecha_clase_var.set(cal.get_date())
            self.btn_fecha_clase.configure(text=self.fecha_clase_var.get())
            popup.destroy()
        
        CTkButton(popup, text="Seleccionar", command=seleccionar,
                fg_color="green", height=35).pack(pady=10)

    def abrir_asistencia(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Seleccione un curso primero")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Registro de Asistencia")
        dialog.geometry("900x700")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (dialog.winfo_screenheight() // 2) - (700 // 2)
        dialog.geometry(f"900x700+{x}+{y}")
        
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_columnconfigure(1, weight=2)
        dialog.grid_rowconfigure(0, weight=1)
        
        left_frame = CTkFrame(dialog,
                             fg_color=COLORES["fondo"],
                             corner_radius=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        left_frame.grid_rowconfigure(5, weight=1)
        
        CTkLabel(left_frame, 
                text="CONTROL DE ASISTENCIA",
                font=self.FUENTES["subtitulo"],
                text_color=COLORES["texto"]).pack(pady=(15, 5))
        
        CTkLabel(left_frame, 
                text="Seleccionar Fecha:",
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(pady=(10, 5))
        
        grupo_frame = CTkFrame(left_frame, fg_color="transparent")
        grupo_frame.pack(pady=10, fill="x", padx=10)
        
        CTkLabel(grupo_frame, 
                text="Grupo:",
                font=self.FUENTES["boton"],
                text_color=COLORES["texto"]).pack(side="left", padx=5)
        
        self.grupo_asistencia_var = ctk.StringVar(value=self.grupo_clase_var.get())
        
        combo_grupo_asistencia = CTkOptionMenu(grupo_frame, 
                                              values=["1", "2", "3", "4", "5"],
                                              variable=self.grupo_asistencia_var,
                                              width=80,
                                              command=lambda x: [self.cargar_estudiantes_asistencia(cal.get_date()), self.guardar_asistencia_auto()],
                                              fg_color=COLORES["secundario"],
                                              button_color=COLORES["primario"],
                                              text_color="white",
                                              font=self.FUENTES["normal"])
        combo_grupo_asistencia.pack(side="left", padx=5)
        
        separador = CTkFrame(left_frame, height=2, fg_color=COLORES["borde"])
        separador.pack(fill="x", padx=10, pady=10)
        
        cal_frame = CTkFrame(left_frame, fg_color=COLORES["tarjeta"])
        cal_frame.pack(pady=5, padx=10)
        
        from datetime import datetime
        try:
            fecha_inicial = datetime.strptime(self.fecha_clase_var.get(), "%d/%m/%Y")
            year, month, day = fecha_inicial.year, fecha_inicial.month, fecha_inicial.day
        except:
            hoy = date.today()
            year, month, day = hoy.year, hoy.month, hoy.day
        
        cal = Calendar(cal_frame, 
                      selectmode='day', 
                      year=year, 
                      month=month, 
                      day=day,
                      locale='es_ES', 
                      font="Arial 10",
                      background=COLORES["primario"],
                      foreground='white',
                      selectbackground=COLORES["acento"],
                      selectforeground='white')
        cal.pack(pady=5)
        
        fecha_label = CTkLabel(left_frame, 
                              text=f"Fecha: {cal.get_date()}",
                              font=self.FUENTES["normal"],
                              text_color=COLORES["texto"])
        fecha_label.pack(pady=10)
        
        btn_frame = CTkFrame(left_frame, fg_color="transparent")
        btn_frame.pack(pady=10, fill="x", padx=10)
        
        CTkButton(btn_frame, 
                 text="Todos Presentes",
                 command=lambda: [self.marcar_todos_asistencia("presente"), self.guardar_asistencia_auto()],
                 fg_color=COLORES["exito"],
                 hover_color="#219A52",
                 font=self.FUENTES["boton"],
                 height=35).pack(pady=2, fill="x")
        CTkButton(btn_frame, 
                 text="Todos Ausentes",
                 command=lambda: [self.marcar_todos_asistencia("ausente"), self.guardar_asistencia_auto()],
                 fg_color=COLORES["peligro"],
                 hover_color="#A93226",
                 font=self.FUENTES["boton"],
                 height=35).pack(pady=2, fill="x")
        CTkButton(btn_frame, 
                 text="Limpiar Todo",
                 command=lambda: [self.marcar_todos_asistencia("sin_marcar"), self.guardar_asistencia_auto()],
                 fg_color=COLORES["secundario"],
                 hover_color=COLORES["primario"],
                 font=self.FUENTES["boton"],
                 height=35).pack(pady=2, fill="x")
        
        CTkButton(left_frame, 
                 text="Cerrar (Guardado automático)",
                 command=lambda: [self.guardar_asistencia_auto(), dialog.destroy()],
                 fg_color=COLORES["acento"],
                 hover_color="#2980B9",
                 height=50,
                 font=self.FUENTES["boton"]).pack(pady=20, fill="x", padx=10)
        
        self.stats_label = CTkLabel(left_frame, 
                                   text="Estadísticas: -",
                                   font=self.FUENTES["normal"],
                                   text_color=COLORES["texto_secundario"])
        self.stats_label.pack(pady=10)
        
        right_frame = CTkFrame(dialog,
                              fg_color=COLORES["tarjeta"],
                              corner_radius=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        right_frame.grid_rowconfigure(1, weight=1)
        
        CTkLabel(right_frame, 
                text="LISTA DE ESTUDIANTES",
                font=self.FUENTES["subtitulo"],
                text_color=COLORES["texto"]).pack(pady=(15, 5))
        
        CTkLabel(right_frame, 
                text="Haga clic en el estado para cambiar",
                font=self.FUENTES["pequeña"],
                text_color=COLORES["texto_secundario"]).pack()
        
        self.asistencia_scroll = CTkScrollableFrame(right_frame,
                                                   fg_color=COLORES["fondo"],
                                                   height=550,
                                                   corner_radius=6)
        self.asistencia_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.checkboxes_asistencia = {}
        
        self.cal_asistencia = cal
        
        self.cargar_estudiantes_asistencia(cal.get_date())
        
        def on_fecha_change(event=None):
            self.guardar_asistencia_auto()
            self.cargar_estudiantes_asistencia(cal.get_date())
            fecha_label.configure(text=f"Fecha: {cal.get_date()}")
            self.fecha_clase_var.set(cal.get_date())
            self.btn_fecha_clase.configure(text=cal.get_date())
        
        cal.bind("<<CalendarSelected>>", on_fecha_change)
        
        def on_closing():
            self.guardar_asistencia_auto()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_closing)

    def cargar_estudiantes_asistencia(self, fecha_str):
        for widget in self.asistencia_scroll.winfo_children():
            widget.destroy()
        self.checkboxes_asistencia = {}
        
        try:
            grupo_asistencia = int(self.grupo_asistencia_var.get())
        except:
            grupo_asistencia = 1
        
        estudiantes = self.db.get_estudiantes(self.current_curso, grupo=grupo_asistencia)
        
        if not estudiantes:
            CTkLabel(self.asistencia_scroll, 
                    text=f"No hay estudiantes en el Grupo {grupo_asistencia}",
                    font=self.FUENTES["normal"],
                    text_color=COLORES["texto_secundario"]).pack(pady=40)
            return
        
        asistencia_previa = self.db.get_asistencia_fecha(self.current_curso, grupo_asistencia, fecha_str)
        
        header = CTkFrame(self.asistencia_scroll,
                         fg_color=COLORES["secundario"],
                         corner_radius=4)
        header.pack(fill="x", padx=5, pady=5)
        
        CTkLabel(header, 
                text="ESTUDIANTE",
                font=self.FUENTES["boton"],
                text_color="white",
                width=300).pack(side="left", padx=10, pady=8)
        CTkLabel(header, 
                text="ESTADO",
                font=self.FUENTES["boton"],
                text_color="white").pack(side="left", padx=20)
        
        separador = CTkFrame(self.asistencia_scroll, height=2, fg_color=COLORES["borde"])
        separador.pack(fill="x", padx=5, pady=2)
        
        def actualizar_stats():
            presentes = sum(1 for d in self.checkboxes_asistencia.values() if d['estado'] == "presente")
            ausentes = sum(1 for d in self.checkboxes_asistencia.values() if d['estado'] == "ausente")
            total = len(self.checkboxes_asistencia)
            
            if hasattr(self, 'stats_label'):
                self.stats_label.configure(
                    text=f"Presentes: {presentes} | Ausentes: {ausentes} | Total: {total}",
                    text_color=COLORES["texto"]
                )
        
        self.actualizar_stats_asistencia = actualizar_stats
        
        for idx, est in enumerate(estudiantes):
            est_id, nombre, grupo, email, carne = est
            est_id_str = str(est_id)
            
            bg_color = COLORES["tarjeta"] if idx % 2 == 0 else COLORES["fondo"]
            
            row = CTkFrame(self.asistencia_scroll,
                          fg_color=bg_color,
                          corner_radius=4)
            row.pack(fill="x", pady=1, padx=5)
            
            nombre_text = f"{nombre}"
            if carne:
                nombre_text += f"  ({carne})"
            
            lbl_nombre = CTkLabel(row, 
                                 text=nombre_text,
                                 font=self.FUENTES["normal"],
                                 text_color=COLORES["texto"],
                                 width=300)
            lbl_nombre.pack(side="left", padx=10, pady=8)
            
            estado_inicial = asistencia_previa.get(est_id_str, "sin_marcar")
            
            btn_toggle = CTkButton(row, 
                                  text="SIN MARCAR",
                                  width=110,
                                  height=30,
                                  font=self.FUENTES["boton"],
                                  corner_radius=4)
            btn_toggle.pack(side="right", padx=10, pady=5)
            
            self.checkboxes_asistencia[est_id_str] = {
                'estado': estado_inicial,
                'boton': btn_toggle
            }
            
            def actualizar_boton(eid=est_id_str):
                datos = self.checkboxes_asistencia[eid]
                estado = datos['estado']
                boton = datos['boton']
                
                if estado == "presente":
                    boton.configure(
                        text="PRESENTE",
                        fg_color=COLORES["exito"],
                        hover_color="#219A52"
                    )
                elif estado == "ausente":
                    boton.configure(
                        text="AUSENTE",
                        fg_color=COLORES["peligro"],
                        hover_color="#A93226"
                    )
                else:
                    boton.configure(
                        text="SIN MARCAR",
                        fg_color=COLORES["secundario"],
                        hover_color=COLORES["primario"]
                    )
                actualizar_stats()
                self.guardar_asistencia_auto()
            
            def toggle_estado(eid=est_id_str):
                datos = self.checkboxes_asistencia[eid]
                if datos['estado'] == "sin_marcar":
                    datos['estado'] = "presente"
                elif datos['estado'] == "presente":
                    datos['estado'] = "ausente"
                else:
                    datos['estado'] = "sin_marcar"
                actualizar_boton(eid)
            
            btn_toggle.configure(command=lambda eid=est_id_str: toggle_estado(eid))
            actualizar_boton(est_id_str)
        
        actualizar_stats()

    def marcar_todos_asistencia(self, estado):
        """Marca todos los estudiantes con el mismo estado"""
        if not hasattr(self, 'checkboxes_asistencia') or not self.checkboxes_asistencia:
            return
        
        for est_id, datos in self.checkboxes_asistencia.items():
            datos['estado'] = estado
            if estado == "presente":
                datos['boton'].configure(
                    text="PRESENTE",
                    fg_color="green",
                    hover_color="darkgreen"
                )
            elif estado == "ausente":
                datos['boton'].configure(
                    text="AUSENTE",
                    fg_color="red",
                    hover_color="darkred"
                )
            else:
                datos['boton'].configure(
                    text="SIN MARCAR",
                    fg_color="gray",
                    hover_color="darkgray"
                )
        
        if hasattr(self, 'actualizar_stats_asistencia'):
            self.actualizar_stats_asistencia()
        
        self.guardar_asistencia_auto()

    def guardar_asistencia_db(self, fecha_str, dialog):
        """Guarda el registro de asistencia en la base de datos"""
        if not hasattr(self, 'checkboxes_asistencia') or not self.checkboxes_asistencia:
            messagebox.showwarning("Advertencia", "No hay estudiantes para guardar")
            return
        
        asistencia_data = {}
        for est_id, datos in self.checkboxes_asistencia.items():
            estado = datos['estado']
            asistencia_data[est_id] = estado
        
        if not asistencia_data:
            messagebox.showwarning("Advertencia", "No hay estudiantes para guardar")
            return
        
        grupo_asistencia = int(self.grupo_asistencia_var.get())
        
        success_del, error_del = self.db.eliminar_asistencia_fecha(self.current_curso, grupo_asistencia, fecha_str)
        
        success, error = self.db.guardar_asistencia(self.current_curso, grupo_asistencia, fecha_str, asistencia_data)
        
        if success:
            stats = self.db.get_estadisticas_asistencia(self.current_curso, grupo_asistencia, fecha_str)
            presentes = stats.get('presente', 0)
            ausentes = stats.get('ausente', 0)
            
            messagebox.showinfo("Exito", 
                            f"Asistencia guardada\n"
                            f"Grupo: {grupo_asistencia} | Fecha: {fecha_str}\n\n"
                            f"Presentes: {presentes}\n"
                            f"Ausentes: {ausentes}")
            dialog.destroy()
        else:
            messagebox.showerror("Error", f"No se pudo guardar la asistencia:\n{error}")

    def guardar_asistencia_auto(self):
        """Guarda la asistencia actual automáticamente sin mostrar mensajes"""
        if not hasattr(self, 'checkboxes_asistencia') or not self.checkboxes_asistencia:
            return
        
        if not self.current_curso:
            return
        
        asistencia_data = {}
        for est_id, datos in self.checkboxes_asistencia.items():
            estado = datos['estado']
            if estado in ["presente", "ausente"]:
                asistencia_data[est_id] = estado
        
        if not asistencia_data:
            return
        
        fecha_str = self.cal_asistencia.get_date() if hasattr(self, 'cal_asistencia') else self.fecha_clase_var.get()
        try:
            grupo_asistencia = int(self.grupo_asistencia_var.get())
        except:
            grupo_asistencia = 1
        
        try:
            self.db.eliminar_asistencia_fecha(self.current_curso, grupo_asistencia, fecha_str)
            self.db.guardar_asistencia(self.current_curso, grupo_asistencia, fecha_str, asistencia_data)
            
            stats = self.db.get_estadisticas_asistencia(self.current_curso, grupo_asistencia, fecha_str)
            presentes = stats.get('presente', 0)
            ausentes = stats.get('ausente', 0)
            
            if hasattr(self, 'stats_label'):
                self.stats_label.configure(text=f"Presentes: {presentes} | Ausentes: {ausentes}")
                
        except Exception as e:
            print(f"Error auto-guardando asistencia: {e}")

    def exportar_clase_pdf(self):
        """Exporta la clase actual a PDF"""
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        if not hasattr(self, 'entry_encabezado_clase') or not self.entry_encabezado_clase.winfo_exists():
            messagebox.showerror("Error", "Error al acceder a los campos de la clase")
            return
        
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        except ImportError:
            messagebox.showerror("Error", "Necesitas instalar reportlab:\npip install reportlab")
            return
        
        try:
            encabezado = self.entry_encabezado_clase.get().strip() if self.entry_encabezado_clase else ""
            topicos = self.entry_topicos.get().strip() if hasattr(self, 'entry_topicos') and self.entry_topicos.winfo_exists() else ""
            observaciones = self.entry_observaciones.get().strip() if hasattr(self, 'entry_observaciones') and self.entry_observaciones.winfo_exists() else ""
            contenido = self.texto_clase.get("1.0", "end-1c").strip() if hasattr(self, 'texto_clase') else ""
        except Exception as e:
            messagebox.showerror("Error", f"Error al leer los campos: {str(e)}")
            return
        
        if not encabezado:
            encabezado = "Clase sin titulo"
        
        nombre_archivo = "".join(c for c in encabezado if c.isalnum() or c in (' ', '-', '_')).rstrip()
        nombre_archivo = nombre_archivo.replace(" ", "_")[:50] or "Clase"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=f"{nombre_archivo}.pdf"
        )
        
        if not filepath:
            return
        
        try:
            self.crear_pdf_clase(filepath, encabezado, topicos, observaciones, contenido)
            messagebox.showinfo("Exito", f"PDF guardado:\n{filepath}")
            if hasattr(self, 'status_clases_label'):
                self.status_clases_label.configure(text=f"PDF exportado: {nombre_archivo[:30]}...")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el PDF:\n{str(e)}")

    def crear_pdf_clase(self, filepath, encabezado, topicos, observaciones, contenido):
        """Crea el PDF de una clase con los datos proporcionados"""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        
        doc = SimpleDocTemplate(filepath, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        elementos = []
        
        estilos = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle(
            'Titulo',
            parent=estilos['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=1
        )
        estilo_subtitulo = ParagraphStyle(
            'Subtitulo',
            parent=estilos['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2e5c8a'),
            spaceAfter=12
        )
        estilo_normal = estilos["BodyText"]
        estilo_normal.fontSize = 11
        estilo_normal.leading = 14
        
        elementos.append(Paragraph("REGISTRO DE CLASE", estilo_titulo))
        elementos.append(Spacer(1, 0.2*inch))
        
        elementos.append(Paragraph(f"<b>{encabezado}</b>", estilo_subtitulo))
        elementos.append(Spacer(1, 0.1*inch))
        
        curso_nombre = "Curso no seleccionado"
        if hasattr(self, 'cursos_data'):
            for nombre, cid in self.cursos_data.items():
                if cid == self.current_curso:
                    curso_nombre = nombre
                    break
        
        elementos.append(Paragraph(f"<b>Curso:</b> {curso_nombre}", estilo_normal))
        elementos.append(Paragraph(f"<b>Fecha de exportacion:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_normal))
        elementos.append(Spacer(1, 0.2*inch))
        
        if topicos:
            elementos.append(Paragraph("<b>TOPICOS A TRATAR:</b>", estilo_subtitulo))
            elementos.append(Paragraph(topicos.replace('\n', '<br/>'), estilo_normal))
            elementos.append(Spacer(1, 0.2*inch))
        
        links = []
        if hasattr(self, 'links_entries'):
            for nombre_entry, url_entry in self.links_entries:
                try:
                    if nombre_entry.winfo_exists() and url_entry.winfo_exists():
                        nombre = nombre_entry.get().strip()
                        url = url_entry.get().strip()
                        if nombre or url:
                            links.append([nombre or "Sin nombre", url or "Sin URL"])
                except:
                    pass
        
        if links:
            elementos.append(Paragraph("<b>LECTURAS ASIGNADAS:</b>", estilo_subtitulo))
            tabla_links = Table(links, colWidths=[2.5*inch, 3.5*inch])
            tabla_links.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elementos.append(tabla_links)
            elementos.append(Spacer(1, 0.2*inch))
        
        if contenido:
            elementos.append(Paragraph("<b>DESARROLLO DE LA CLASE:</b>", estilo_subtitulo))
            contenido_html = contenido.replace('\n', '<br/>')
            elementos.append(Paragraph(contenido_html, estilo_normal))
            elementos.append(Spacer(1, 0.2*inch))
        
        if observaciones:
            elementos.append(Paragraph("<b>OBSERVACIONES:</b>", estilo_subtitulo))
            elementos.append(Paragraph(observaciones.replace('\n', '<br/>'), estilo_normal))
        
        doc.build(elementos)

    def exportar_todas_clases_pdf(self):
        """Exporta todas las clases guardadas en un solo PDF"""
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        except ImportError:
            messagebox.showerror("Error", "Necesitas instalar reportlab:\npip install reportlab")
            return
        
        clases_db = self.db.get_clases(self.current_curso)
        
        if not clases_db:
            messagebox.showwarning("Advertencia", "No hay clases guardadas para exportar")
            return
        
        curso_nombre = "Curso"
        if hasattr(self, 'cursos_data'):
            for nombre, cid in self.cursos_data.items():
                if cid == self.current_curso:
                    curso_nombre = nombre
                    break
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialfile=f"Clases_{curso_nombre.replace(' ', '_')}.pdf"
        )
        
        if not filepath:
            return
        
        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=18)
            
            elementos = []
            
            estilos = getSampleStyleSheet()
            estilo_titulo = ParagraphStyle('Titulo', parent=estilos['Heading1'], fontSize=20, 
                                          textColor=colors.HexColor('#1f4788'), spaceAfter=30, alignment=1)
            estilo_subtitulo = ParagraphStyle('Subtitulo', parent=estilos['Heading2'], fontSize=14,
                                             textColor=colors.HexColor('#2e5c8a'), spaceAfter=12)
            estilo_normal = estilos["BodyText"]
            estilo_normal.fontSize = 11
            
            elementos.append(Spacer(1, 2*inch))
            elementos.append(Paragraph("REGISTRO DE CLASES", estilo_titulo))
            elementos.append(Spacer(1, 0.5*inch))
            elementos.append(Paragraph(f"<b>Curso:</b> {curso_nombre}", estilo_subtitulo))
            elementos.append(Paragraph(f"<b>Total de clases:</b> {len(clases_db)}", estilo_normal))
            elementos.append(Paragraph(f"<b>Fecha de exportacion:</b> {datetime.now().strftime('%d/%m/%Y')}", estilo_normal))
            elementos.append(PageBreak())
            
            for idx, clase_row in enumerate(clases_db, 1):
                clase_id = clase_row[0]
                
                clase_data = self.db.get_clase_por_id(clase_id)
                
                if not clase_data:
                    continue
                
                elementos.append(Paragraph(f"CLASE {idx}", estilo_titulo))
                elementos.append(Paragraph(f"<b>{clase_data.get('encabezado', 'Sin titulo')}</b>", estilo_subtitulo))
                
                topicos = clase_data.get('topicos', '')
                if topicos:
                    elementos.append(Paragraph("<b>Topicos:</b> " + topicos, estilo_normal))
                
                links = clase_data.get('links', [])
                if links:
                    elementos.append(Paragraph("<b>Lecturas asignadas:</b>", estilo_normal))
                    for link in links:
                        elementos.append(Paragraph(f"• {link['nombre']}: {link['url']}", estilo_normal))
                
                contenido = clase_data.get('contenido', '')
                if contenido:
                    if len(contenido) > 1000:
                        contenido = contenido[:1000] + "..."
                    elementos.append(Paragraph("<b>Desarrollo:</b><br/>" + contenido.replace('\n', '<br/>'), estilo_normal))
                
                obs = clase_data.get('observaciones', '')
                if obs:
                    elementos.append(Paragraph("<b>Observaciones:</b> " + obs, estilo_normal))
                
                elementos.append(Spacer(1, 0.3*inch))
                elementos.append(PageBreak())
            
            if elementos and isinstance(elementos[-1], PageBreak):
                elementos.pop()
            
            doc.build(elementos)
            messagebox.showinfo("Exito", f"PDF con {len(clases_db)} clases guardado:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el PDF:\n{str(e)}")

if __name__ == "__main__":
    app = GestorNotasApp()
    app.mainloop()