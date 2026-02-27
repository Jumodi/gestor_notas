import customtkinter as ctk
from customtkinter import CTk, CTkFrame, CTkLabel, CTkButton, CTkOptionMenu, CTkEntry, CTkScrollableFrame, CTkTabview, CTkInputDialog, CTkToplevel
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from database import DatabaseManager
# NUEVO: Sistema de sincronizacion por archivo
from sync_file import FileSyncManager
import os
import threading
import platform
import time
import sys
from tkcalendar import Calendar
from datetime import datetime, date
import json



SISTEMA = platform.system()

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

#PRUEBA DE CÓDIGO 


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

SISTEMA = platform.system()

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class GestorNotasApp(CTk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de Evaluaciones Universitarias")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        self.db = DatabaseManager(DB_PATH)
        # NUEVO: Sistema de sincronizacion por archivo compartido
        self.file_sync = FileSyncManager(DB_PATH)
        self.current_curso = None
        self.current_evaluacion = None
        self.entries_notas = {}
        self.auto_sync_enabled = False
        self.clase_actual_id = None
        self.setup_ui()
        self.load_cursos()
        # Verificar estado de sincronizacion al iniciar
        self.after(1000, self.verificar_sincronizacion_inicio)


    def sincronizar_manual(self):
        """Abre dialogo de sincronizacion por archivo compartido"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Sincronizacion por Archivo Compartido")
        dialog.geometry("500x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # Centrar
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"500x600+{x}+{y}")
        
        CTkLabel(dialog, text="Sincronizacion de Datos", 
                font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        
        # Estado actual
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
        
        # Carpeta configurada
        CTkLabel(dialog, text="Carpeta de sincronizacion:", 
                font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        folder_text = self.file_sync.sync_folder or "No configurada"
        lbl_folder = CTkLabel(dialog, text=folder_text, font=ctk.CTkFont(size=11))
        lbl_folder.pack(anchor="w", padx=20)
        
        # Botones principales
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
        
        # Configuracion
        CTkFrame(dialog, height=2, fg_color="gray").pack(fill="x", padx=20, pady=20)
        
        CTkLabel(dialog, text="Configuracion", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20)
        
        # Detectar carpetas comunes
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
        
        # Seleccion manual
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
        
        # Resolver conflicto (solo visible si hay conflicto)
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
        
        # Actualizar status bar
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
            btn.configure(fg_color="transparent", border_color="gray")
        if nombre_curso in self.curso_buttons:
            self.curso_buttons[nombre_curso].configure(fg_color="blue", border_color="blue")
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
        # Limpiar scroll
        for widget in self.cursos_scroll.winfo_children():
            widget.destroy()
        
        cursos = self.db.get_cursos()
        self.cursos_data = {}
        self.curso_buttons = {}
        
        if cursos:
            for curso in cursos:
                curso_id, nombre, descripcion, total_est, total_eval = curso
                self.cursos_data[nombre] = curso_id
                
                # Texto con info compacta
                btn_text = f"{nombre}\n({total_est} est, {total_eval} eval)"
                
                # Frame contenedor para mejor control
                btn_frame = CTkFrame(self.cursos_scroll, fg_color="transparent")
                btn_frame.pack(fill="x", pady=2, padx=5)
                btn_frame.grid_columnconfigure(0, weight=1)
                
                # Botón con texto ajustado (wraplength)
                btn = CTkButton(
                    btn_frame, 
                    text=btn_text, 
                    command=lambda n=nombre: self.seleccionar_curso(n),
                    fg_color="transparent",
                    border_width=2,
                    border_color="gray",
                    hover_color="gray25",
                    anchor="w",
                    height=50,  
                    corner_radius=8,
                    font=ctk.CTkFont(size=11)  # Fuente ligeramente más pequeña
                )
                # Configurar wraplength para que el texto haga salto de línea
                btn._text_label.configure(wraplength=280, justify="left")
                # Forzar expansión horizontal
                btn.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
                
                self.curso_buttons[nombre] = btn
                self.agregar_tooltip(btn, f"Curso: {nombre}\nDescripción: {descripcion or 'Sin descripción'}")
            
            # Seleccionar primero
            self.seleccionar_curso(cursos[0][1])
        else:
            CTkLabel(self.cursos_scroll, text="No hay cursos").pack(pady=10)
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
            btn.configure(fg_color="transparent", border_color="gray")
        if nombre_eval in self.eval_buttons:
            self.eval_buttons[nombre_eval].configure(fg_color="green", border_color="green")
        self.current_evaluacion = self.evals_data.get(nombre_eval)
        if self.current_evaluacion:
            self.load_estudiantes_notas()
        else:
            self.limpiar_tab_notas()

    def load_evaluaciones(self):
        if not self.current_curso:
            return
        
        # Limpiar scroll
        for widget in self.evals_scroll.winfo_children():
            widget.destroy()
        
        evals = self.db.get_evaluaciones(self.current_curso)
        self.evals_data = {}
        self.eval_buttons = {}
        
        if evals:
            for eval in evals:
                eval_id, nombre, puntos_max, orden, fecha = eval
                self.evals_data[nombre] = eval_id
                
                # Texto: nombre en línea 1, puntos en línea 2
                btn_text = f"{nombre}\n(Máx: {puntos_max} pts)"
                
                # Frame contenedor
                btn_frame = CTkFrame(self.evals_scroll, fg_color="transparent")
                btn_frame.pack(fill="x", pady=2, padx=5)
                btn_frame.grid_columnconfigure(0, weight=1)
                
                btn = CTkButton(
                    btn_frame,
                    text=btn_text,
                    command=lambda n=nombre: self.seleccionar_evaluacion(n),
                    fg_color="transparent",
                    border_width=2,
                    border_color="gray",
                    hover_color="gray25",
                    anchor="w",
                    height=50,  # Aumentado para permitir 2 líneas
                    corner_radius=8,
                    font=ctk.CTkFont(size=11)  # Fuente ligeramente más pequeña
                )
                # Configurar wraplength para salto de línea automático
                btn._text_label.configure(wraplength=280, justify="left")
                btn.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
                
                self.eval_buttons[nombre] = btn
                self.agregar_tooltip(btn, f"Evaluación: {nombre}\nMáximo: {puntos_max} puntos")
            
            # Seleccionar primera evaluación
            self.seleccionar_evaluacion(evals[0][1])
        else:
            CTkLabel(self.evals_scroll, text="Sin evaluaciones").pack(pady=10)
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
        """Abre el editor de rubrica para la evaluacion seleccionada"""
        if not self.current_evaluacion:
            messagebox.showwarning("Advertencia", "Selecciona una evaluacion primero")
            return
        
        # Obtener info de la evaluacion
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
        if not eval_info:
            return
        
        eval_nombre = eval_info[1]
        puntos_max_eval = eval_info[2]
        
        # Crear ventana de edicion de rubrica
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Editar Rubrica - {eval_nombre}")
        dialog.geometry("700x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # Centrar
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (600 // 2)
        dialog.geometry(f"700x600+{x}+{y}")
        
        # Header
        CTkLabel(dialog, text=f"Rubrica: {eval_nombre}", 
                font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 5))
        
        CTkLabel(dialog, text=f"Puntos maximos de la evaluacion: {puntos_max_eval}", 
                font=ctk.CTkFont(size=14), text_color="gray").pack()
        
        # Frame para mostrar total asignado
        frame_total = CTkFrame(dialog)
        frame_total.pack(fill="x", padx=20, pady=10)
        
        self.lbl_total_rubrica = CTkLabel(frame_total, 
                                           text="Total asignado en rubrica: 0", 
                                           font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_total_rubrica.pack(side="left", padx=10)
        
        self.lbl_diferencia = CTkLabel(frame_total, 
                                        text="(Faltan: 20)", 
                                        font=ctk.CTkFont(size=12))
        self.lbl_diferencia.pack(side="left", padx=10)
        
        # Frame scrollable para criterios existentes
        scroll_criterios = CTkScrollableFrame(dialog, label_text="Criterios de la Rubrica", height=300)
        scroll_criterios.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.frame_criterios_list = scroll_criterios
        self.criterios_entries = []  # Lista para guardar referencias
        
        def actualizar_total():
            """Actualiza el total de puntos asignados"""
            total = 0
            for entry_info in self.criterios_entries:
                try:
                    puntos = float(entry_info['puntos'].get() or 0)
                    total += puntos
                except:
                    pass
            
            self.lbl_total_rubrica.configure(text=f"Total asignado en rubrica: {total}")
            
            diferencia = puntos_max_eval - total
            if diferencia == 0:
                color = "green"
                texto = "(Completo)"
            elif diferencia > 0:
                color = "orange"
                texto = f"(Faltan: {diferencia})"
            else:
                color = "red"
                texto = f"(Excede por: {abs(diferencia)})"
            
            self.lbl_diferencia.configure(text=texto, text_color=color)
        
        def agregar_fila_criterio(nombre="", puntos="", criterio_id=None):
            """Agrega una fila para un criterio"""
            frame = CTkFrame(self.frame_criterios_list)
            frame.pack(fill="x", pady=2, padx=5)
            
            entry_nombre = CTkEntry(frame, placeholder_text="Nombre del criterio", width=350)
            entry_nombre.pack(side="left", padx=2, fill="x", expand=True)
            if nombre:
                entry_nombre.insert(0, nombre)
            
            entry_puntos = CTkEntry(frame, placeholder_text="Pts", width=80)
            entry_puntos.pack(side="left", padx=2)
            if puntos:
                entry_puntos.insert(0, str(puntos))
            
            # Guardar referencia
            criterio_info = {
                'frame': frame,
                'nombre': entry_nombre,
                'puntos': entry_puntos,
                'id': criterio_id
            }
            self.criterios_entries.append(criterio_info)
            
            # Bind para actualizar total
            entry_puntos.bind("<KeyRelease>", lambda e: actualizar_total())
            
            def eliminar_fila():
                frame.destroy()
                self.criterios_entries.remove(criterio_info)
                actualizar_total()
                # Si tenia ID, marcar para eliminar
                if criterio_id:
                    criterio_info['eliminar'] = True
            
            CTkButton(frame, text="X", width=30, fg_color="red", 
                     command=eliminar_fila).pack(side="left", padx=2)
        
        # Cargar criterios existentes
        criterios_existentes = self.db.get_criterios_rubrica(self.current_evaluacion)
        if criterios_existentes:
            for crit in criterios_existentes:
                crit_id, nombre, puntos, orden = crit
                agregar_fila_criterio(nombre, puntos, crit_id)
        else:
            # Agregar filas vacias por defecto
            agregar_fila_criterio()
            agregar_fila_criterio()
        
        actualizar_total()
        
        # Boton agregar mas criterios
        CTkButton(dialog, text="+ Agregar Criterio", 
                 command=lambda: agregar_fila_criterio()).pack(pady=5)
        
        # Botones de accion
        btn_frame = CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        def guardar_rubrica():
            """Guarda todos los criterios de la rubrica"""
            # Validar que sume el total
            total = 0
            criterios_validos = []
            
            for entry_info in self.criterios_entries:
                nombre = entry_info['nombre'].get().strip()
                try:
                    puntos = float(entry_info['puntos'].get() or 0)
                except:
                    puntos = 0
                
                if nombre:  # Solo si tiene nombre
                    total += puntos
                    criterios_validos.append({
                        'nombre': nombre,
                        'puntos': puntos,
                        'id': entry_info.get('id'),
                        'eliminar': entry_info.get('eliminar', False)
                    })
            
            if total != puntos_max_eval:
                messagebox.showerror("Error", 
                    f"Los puntos de la rubrica deben sumar exactamente {puntos_max_eval}.\n"
                    f"Actualmente suman: {total}")
                return
            
            # Guardar en base de datos
            try:
                # Eliminar los marcados para eliminar
                for c in criterios_validos:
                    if c['eliminar'] and c['id']:
                        self.db.eliminar_criterio_rubrica(c['id'])
                
                # Agregar o actualizar los demas
                for idx, c in enumerate(criterios_validos):
                    if not c['eliminar']:
                        if c['id']:
                            # Actualizar existente
                            self.db.actualizar_criterio_rubrica(c['id'], c['nombre'], c['puntos'], idx)
                        else:
                            self.db.agregar_criterio_rubrica(
                                self.current_evaluacion, 
                                c['nombre'], 
                                c['puntos'],
                                idx
                            )
                
                messagebox.showinfo("Exito", "Rubrica guardada correctamente")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
        
        CTkButton(btn_frame, text="Guardar Rubrica", 
                 command=guardar_rubrica, fg_color="green",
                 height=40, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5, fill="x", expand=True)
        
        CTkButton(btn_frame, text="Cancelar", 
                 command=dialog.destroy, fg_color="gray").pack(side="left", padx=5, fill="x", expand=True)

    def agregar_estudiante(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        # Crear diálogo personalizado para todos los campos
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nuevo Estudiante")
        dialog.geometry("450x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Centrar
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"450x400+{x}+{y}")
        
        CTkLabel(dialog, text="👤 Nuevo Estudiante", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        
        # Frame de campos
        frame_campos = CTkFrame(dialog)
        frame_campos.pack(fill="x", padx=30, pady=10)
        
        # Nombre
        CTkLabel(frame_campos, text="Nombre completo:*", 
                font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        entry_nombre = CTkEntry(frame_campos, width=350, placeholder_text="Ej: Juan Pérez")
        entry_nombre.pack(fill="x", pady=5)
        
        # Carné
        CTkLabel(frame_campos, text="Número de carné:", 
                font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        entry_carne = CTkEntry(frame_campos, width=350, placeholder_text="Ej: 20240001")
        entry_carne.pack(fill="x", pady=5)
        
        # Grupo
        CTkLabel(frame_campos, text="Grupo:*", 
                font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        entry_grupo = CTkEntry(frame_campos, width=350, placeholder_text="1")
        entry_grupo.insert(0, "1")
        entry_grupo.pack(fill="x", pady=5)
        
        # Email
        CTkLabel(frame_campos, text="Email:", 
                font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        entry_email = CTkEntry(frame_campos, width=350, placeholder_text="ejemplo@correo.com")
        entry_email.pack(fill="x", pady=5)
        
        CTkLabel(dialog, text="* Campos obligatorios", 
                font=ctk.CTkFont(size=10), text_color="gray").pack()
        
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
        
        CTkButton(dialog, text="Guardar Estudiante", 
                 command=guardar, fg_color="green", 
                 height=40, font=ctk.CTkFont(weight="bold")).pack(pady=20)

    def agregar_varios_estudiantes(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Agregar Varios Estudiantes")
        dialog.geometry("500x500")
        dialog.transient(self)
        dialog.grab_set()
        
        CTkLabel(dialog, text="👥 Agregar Varios Estudiantes", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))
        
        # Campo para grupo
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
        
        # Crear lista con info completa
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
        
        # Combo con nombres
        nombres = [info[0] for info in lista_info]
        est_var = ctk.StringVar(value=nombres[0])
        menu = CTkOptionMenu(dialog, values=nombres, variable=est_var, width=400)
        menu.pack(pady=10)
        
        # Frame para campos de edición
        frame_edit = CTkFrame(dialog)
        frame_edit.pack(fill="x", padx=30, pady=10)
        
        # Variables para los entries
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
        
        # Campos de edición
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
        
        # Cargar datos iniciales
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
        """Carga estudiantes organizados por grupos en tabs separados"""
        # Limpiar frame anterior
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        self.entries_notas = {}
        
        if not self.current_curso:
            CTkLabel(self.scroll_frame, text="Selecciona un curso primero", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
            return
        
        if not self.current_evaluacion:
            CTkLabel(self.scroll_frame, text="Selecciona una evaluacion primero", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
            return
        
        # Obtener info de la evaluación
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
        
        if not eval_info:
            CTkLabel(self.scroll_frame, text="Error: Evaluación no encontrada", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
            return
        
        eval_nombre = eval_info[1]
        eval_puntos_max = eval_info[2]
        
        # Header con info de evaluación
        header_frame = CTkFrame(self.scroll_frame)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        CTkLabel(header_frame, 
                text=f"Evaluación: {eval_nombre} (Máx: {eval_puntos_max} pts)", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10)
        
        self.guardado_status_label = CTkLabel(header_frame, 
                                              text="Estado: Listo", 
                                              font=ctk.CTkFont(size=12),
                                              text_color="gray")
        self.guardado_status_label.pack(side="right", padx=10)
        
        # Obtener todos los estudiantes y organizar por grupos
        todos_estudiantes = self.db.get_estudiantes(self.current_curso)
        
        if not todos_estudiantes:
            CTkLabel(self.scroll_frame, 
                    text="No hay estudiantes en este curso. Agrega estudiantes usando el botón Agregar Estudiante.", 
                    font=ctk.CTkFont(size=12)).pack(pady=20)
            return
        
        # Organizar por grupos
        grupos = {}
        for est in todos_estudiantes:
            # est = (id, nombre, grupo, email, carne)
            grupo_num = est[2]
            if grupo_num not in grupos:
                grupos[grupo_num] = []
            grupos[grupo_num].append(est)
        
        # Crear Tabview para los grupos - OCUPAR TODO EL ESPACIO VERTICAL
        self.tabview_grupos = CTkTabview(self.scroll_frame, height=550)
        self.tabview_grupos.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Crear un tab por cada grupo
        for grupo_num in sorted(grupos.keys()):
            estudiantes_grupo = grupos[grupo_num]
            tab_nombre = f"Grupo {grupo_num}"
            
            tab = self.tabview_grupos.add(tab_nombre)
            self.crear_contenido_grupo(tab, estudiantes_grupo, eval_puntos_max)
        
        self.status_label.configure(text=f"{len(todos_estudiantes)} estudiantes en {len(grupos)} grupos")

    def crear_contenido_grupo(self, tab_padre, estudiantes, puntos_max):
        """Crea el contenido de un tab de grupo con lista de estudiantes clickeables"""
        
        # Frame contenedor con ancho mínimo
        container = CTkFrame(tab_padre)
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Frame scrollable para la lista con ancho y alto fijos
        scroll_grupo = CTkScrollableFrame(container, 
                                         label_text=f"Estudiantes ({len(estudiantes)})", 
                                         width=850,
                                         height=480)  # Altura grande para ver más estudiantes
        scroll_grupo.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header de columnas - anchos ajustados para que quepan en pantalla
        header = CTkFrame(scroll_grupo)
        header.pack(fill="x", padx=5, pady=2)
        header.grid_columnconfigure(0, weight=3, minsize=300)  # Nombre más ancho
        header.grid_columnconfigure(1, weight=0, minsize=120)   # Nota
        header.grid_columnconfigure(2, weight=1, minsize=200)   # Observaciones
        
        CTkLabel(header, text="Estudiante", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        CTkLabel(header, text="Nota", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=1, padx=10, pady=5, sticky="ew")
        CTkLabel(header, text="Observaciones", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=2, padx=10, pady=5, sticky="w")
        
        CTkFrame(scroll_grupo, height=2, fg_color="gray").pack(fill="x", padx=5, pady=2)
        
        # Filas de estudiantes
        for est in estudiantes:
            est_id, nombre, grupo_num, email, carne = est
            
            row = CTkFrame(scroll_grupo, height=30)  # Altura fija más compacta
            row.pack(fill="x", padx=5, pady=1)  # Menos padding vertical
            row.pack_propagate(False)  # Forzar altura fija
            row.grid_columnconfigure(0, weight=3, minsize=300)
            row.grid_columnconfigure(1, weight=0, minsize=120)
            row.grid_columnconfigure(2, weight=1, minsize=200)
            
            # --- NOMBRE CLICKEABLE ---
            nombre_container = CTkFrame(row, fg_color="transparent")
            nombre_container.grid(row=0, column=0, padx=10, pady=2, sticky="w")
            
            lbl_nombre = CTkLabel(nombre_container, 
                                 text=f" {nombre}", 
                                 font=ctk.CTkFont(size=12),
                                 cursor="hand2")
            lbl_nombre.pack(anchor="w")
            
            # Bind click para mostrar modal
            lbl_nombre.bind("<Button-1>", 
                           lambda e, est=est: self.mostrar_modal_estudiante(est))
            
            # Efecto hover
            def on_enter(e, widget=lbl_nombre):
                widget.configure(text_color="blue", font=ctk.CTkFont(size=12, weight="bold"))
            def on_leave(e, widget=lbl_nombre):
                widget.configure(text_color=["black", "white"], font=ctk.CTkFont(size=12))
            
            lbl_nombre.bind("<Enter>", on_enter)
            lbl_nombre.bind("<Leave>", on_leave)
            
            # --- CAMPO DE NOTA ---
            nota_existente, obs_existente = self.db.get_nota(est_id, self.current_evaluacion)
            
            # Verificar si la evaluacion tiene rubrica
            tiene_rubrica = len(self.db.get_criterios_rubrica(self.current_evaluacion)) > 0
            
            nota_container = CTkFrame(row, fg_color="transparent")
            nota_container.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            
            nota_var = ctk.StringVar(value=str(nota_existente) if nota_existente is not None else "")
            entry_nota = CTkEntry(nota_container, width=80, textvariable=nota_var, 
                     justify="center", placeholder_text=f"0-{puntos_max}")
            entry_nota.pack(side="left", padx=2)
            
            # Indicador visual diferente si tiene rubrica
            if tiene_rubrica and nota_existente:
                estado_text = "[R]"  # Indicador de rubrica
                tooltip_text = "Calificado por rubrica - Clic para editar"
            elif nota_existente:
                estado_text = "OK"
                tooltip_text = "Calificado"
            else:
                estado_text = "-"
                tooltip_text = "Sin calificar - Clic para calificar"
            
            estado_color = "green" if nota_existente else "gray"
            estado_label = CTkLabel(nota_container, text=estado_text, width=25, 
                                   text_color=estado_color, font=ctk.CTkFont(size=11, weight="bold"))
            estado_label.pack(side="left", padx=2)
            self.agregar_tooltip(estado_label, tooltip_text)
            
            # --- OBSERVACIONES ---
            obs_var = ctk.StringVar(value=obs_existente or "")
            entry_obs = CTkEntry(row, textvariable=obs_var, placeholder_text="Obs...", width=150)
            entry_obs.grid(row=0, column=2, padx=10, pady=2, sticky="ew")
            
            # --- GUARDADO AUTOMÁTICO ---
            def guardar_al_salir(event, eid=est_id, nv=nota_var, ov=obs_var, el=estado_label, pm=puntos_max):
                self.guardar_nota_auto(eid, nv, ov, el, pm)
            
            entry_nota.bind("<FocusOut>", guardar_al_salir)
            entry_obs.bind("<FocusOut>", guardar_al_salir)
            entry_nota.bind("<Return>", guardar_al_salir)
            entry_obs.bind("<Return>", guardar_al_salir)
            
            self.entries_notas[est_id] = (nota_var, obs_var, estado_label)

    
    def mostrar_modal_estudiante(self, estudiante):
        """Muestra modal con datos del estudiante y rubrica de evaluacion"""
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
                mensaje_extra="\n\nEsta evaluacion no tiene rubrica definida.\nVe a 'Rubrica' para crearla.")
            return
        
        # Calcular altura necesaria basada en numero de criterios
        # Aumentado el espacio por criterio y el espacio base para asegurar visibilidad de botones
        altura_por_criterio = 90
        altura_minima = 550
        altura_maxima = 900
        # Altura base aumentada para asegurar espacio para header, info, titulo, total y botones
        altura_base = 400
        altura_calculada = min(max(altura_minima, altura_base + (len(criterios) * altura_por_criterio)), altura_maxima)
        
        # Crear modal con tamano dinamico
        modal = ctk.CTkToplevel(self)
        modal.title(f"Calificar: {nombre}")
        modal.geometry(f"650x{altura_calculada}")
        modal.transient(self)
        modal.grab_set()
        
        # Centrar en pantalla
        modal.update_idletasks()
        x = (modal.winfo_screenwidth() // 2) - (650 // 2)
        y = (modal.winfo_screenheight() // 2) - (altura_calculada // 2)
        modal.geometry(f"650x{altura_calculada}+{x}+{y}")
        
        # Frame principal que ocupa todo
        main_frame = CTkFrame(modal)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header compacto
        header_frame = CTkFrame(main_frame, fg_color="blue", height=50)
        header_frame.pack(fill="x", pady=(0, 5))
        header_frame.pack_propagate(False)
        
        CTkLabel(header_frame, text=f"{nombre}", 
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="white").pack(pady=5)
        
        # Info basica en una linea (mas compacto)
        info_frame = CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=2)
        
        info_text = f"Grupo: {grupo}  |  "
        info_text += f"Carne: {carne or 'N/A'}  |  "
        info_text += f"Email: {email or 'N/A'}"
        
        CTkLabel(info_frame, text=info_text, 
                font=ctk.CTkFont(size=11),
                text_color="gray").pack(pady=2)
        
        # Titulo de rubrica compacto
        title_frame = CTkFrame(main_frame)
        title_frame.pack(fill="x", pady=5)
        
        CTkLabel(title_frame, text=f"{eval_nombre}", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=5)
        CTkLabel(title_frame, text=f"(Max: {puntos_max_eval} pts)", 
                font=ctk.CTkFont(size=11),
                text_color="gray").pack(side="left", padx=5)
        
        # Frame scrollable para criterios - altura flexible pero con minimo garantizado
        # Calcular altura del scroll dejando espacio fijo para elementos inferiores
        altura_fija_inferior = 180  # Espacio reservado para total, botones y margenes
        altura_scroll = max(200, altura_calculada - 320)  # Minimo 200px para el scroll
        
        scroll_rubrica = CTkScrollableFrame(main_frame, 
                                           label_text=f"Criterios ({len(criterios)})", 
                                           height=altura_scroll)
        scroll_rubrica.pack(fill="both", expand=True, pady=5)
        
        # Obtener calificaciones previas
        calificaciones_previas = self.db.get_calificaciones_rubrica_estudiante(est_id, self.current_evaluacion)
        
        # Diccionario para guardar entries
        entries_criterios = {}
        
        # Crear campos para cada criterio (mas compactos)
        for crit in calificaciones_previas:
            crit_id, nombre_criterio, puntos_max, puntos_obtenidos, obs = crit
            
            # Frame mas compacto para cada criterio
            frame_crit = CTkFrame(scroll_rubrica)
            frame_crit.pack(fill="x", pady=3, padx=3)
            
            # Nombre y maximo en una linea
            header_crit = CTkFrame(frame_crit, fg_color="transparent")
            header_crit.pack(fill="x", padx=5, pady=(3, 0))
            
            CTkLabel(header_crit, text=nombre_criterio, 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
            CTkLabel(header_crit, text=f" (max: {puntos_max})", 
                    font=ctk.CTkFont(size=10),
                    text_color="gray").pack(side="left", padx=5)
            
            # Frame para inputs en una linea
            input_frame = CTkFrame(frame_crit, fg_color="transparent")
            input_frame.pack(fill="x", padx=5, pady=3)
            
            # Entry para puntos (mas compacto)
            var_puntos = ctk.StringVar(value=str(puntos_obtenidos) if puntos_obtenidos > 0 else "")
            entry_puntos = CTkEntry(input_frame, width=80, height=28,
                                   textvariable=var_puntos,
                                   placeholder_text=f"0-{puntos_max}")
            entry_puntos.pack(side="left", padx=2)
            
            CTkLabel(input_frame, text="/", font=ctk.CTkFont(size=12)).pack(side="left", padx=2)
            CTkLabel(input_frame, text=f"{puntos_max}", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=2)
            
            # Entry para observaciones (mas ancho)
            var_obs = ctk.StringVar(value=obs or "")
            entry_obs = CTkEntry(input_frame, placeholder_text="Obs...", 
                                textvariable=var_obs, width=300, height=28)
            entry_obs.pack(side="left", padx=10, fill="x", expand=True)
            
            # Guardar referencia
            entries_criterios[crit_id] = {
                'puntos': var_puntos,
                'obs': var_obs,
                'max': puntos_max,
                'nombre': nombre_criterio
            }
        
        # Frame inferior fijo (no se mueve con el scroll) - SIEMPRE VISIBLE
        bottom_frame = CTkFrame(main_frame)
        bottom_frame.pack(fill="x", pady=5)
        
        # Label para mostrar total (mas visible)
        lbl_total = CTkLabel(bottom_frame, 
                            text=f"Total: 0 / {puntos_max_eval}",
                            font=ctk.CTkFont(size=18, weight="bold"))
        lbl_total.pack(pady=5)
        
        def calcular_total():
            total = 0
            for entries in entries_criterios.values():
                try:
                    puntos = float(entries['puntos'].get() or 0)
                    total += puntos
                except:
                    pass
            
            color = "green" if total == puntos_max_eval else "orange" if total < puntos_max_eval else "red"
            lbl_total.configure(text=f"Total: {total} / {puntos_max_eval}", text_color=color)
            return total
        
        # Calcular inicial
        calcular_total()
        
        # Actualizar total cuando cambien los valores
        for entries in entries_criterios.values():
            entries['puntos'].trace_add("write", lambda *args: calcular_total())
        
        # ========== BOTONES ==========
        btn_frame = CTkFrame(bottom_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        
        def aceptar_y_guardar():
            """Guarda todos los criterios y la nota total"""
            try:
                total = 0
                
                # Guardar cada criterio
                for crit_id, entries in entries_criterios.items():
                    puntos_str = entries['puntos'].get().strip()
                    puntos = float(puntos_str) if puntos_str else 0
                    obs = entries['obs'].get().strip()
                    
                    # Validar maximo del criterio
                    if puntos > entries['max']:
                        messagebox.showerror("Error", 
                            f"'{entries['nombre']}': maximo {entries['max']} puntos")
                        return
                    
                    # Guardar en rubrica
                    self.db.guardar_calificacion_rubrica(est_id, crit_id, puntos, obs)
                    total += puntos
                
                # Validar total no exceda
                if total > puntos_max_eval:
                    messagebox.showerror("Error", 
                        f"Total ({total}) excede el maximo ({puntos_max_eval})")
                    return
                
                # Guardar en tabla de notas
                self.db.guardar_nota(est_id, self.current_evaluacion, total, "Calificado por rubrica")
                
                # Actualizar vista
                self.load_estudiantes_notas()
                self.actualizar_resumen()
                
                # Cerrar modal
                modal.destroy()
                
                # Mostrar confirmacion
                self.status_label.configure(
                    text=f"Guardado: {nombre} = {total}/{puntos_max_eval} pts",
                    text_color="green"
                )
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {str(e)}")
        
        # Botones grandes y visibles
        CTkButton(btn_frame, text="ACEPTAR", 
                 command=aceptar_y_guardar,
                 fg_color="green", 
                 hover_color="darkgreen",
                 height=45,
                 font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=5, fill="x", expand=True)
        
        CTkButton(btn_frame, text="Cancelar", 
                 command=modal.destroy,
                 fg_color="gray", 
                 hover_color="darkgray",
                 height=45,
                 font=ctk.CTkFont(size=14)).pack(side="left", padx=5, fill="x", expand=True)
        
    def mostrar_modal_estudiante_simple(self, estudiante, mensaje_extra=""):
        """Muestra solo los datos basicos del estudiante (sin rubrica)"""
        est_id, nombre, grupo, email, carne = estudiante
        
        modal = CTkToplevel(self)
        modal.title(f"Datos del Estudiante")
        modal.geometry("400x350")
        modal.transient(self)
        modal.grab_set()
        
        # Centrar
        modal.update_idletasks()
        x = (modal.winfo_screenwidth() // 2) - (400 // 2)
        y = (modal.winfo_screenheight() // 2) - (350 // 2)
        modal.geometry(f"400x350+{x}+{y}")
        
        CTkLabel(modal, text="Estudiante", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        CTkLabel(modal, text=nombre, font=ctk.CTkFont(size=18, weight="bold")).pack()
        
        frame_datos = CTkFrame(modal)
        frame_datos.pack(fill="x", padx=30, pady=20)
        
        CTkLabel(frame_datos, text="Grupo:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        CTkLabel(frame_datos, text=str(grupo)).grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        CTkLabel(frame_datos, text="Carne:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        CTkLabel(frame_datos, text=carne or "No registrado").grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        CTkLabel(frame_datos, text="Email:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        CTkLabel(frame_datos, text=email or "No registrado").grid(row=2, column=1, sticky="w", padx=10, pady=5)
        
        if mensaje_extra:
            CTkLabel(modal, text=mensaje_extra, 
                    font=ctk.CTkFont(size=12),
                    text_color="orange").pack(pady=10)
        
        CTkButton(modal, text="Cerrar", command=modal.destroy, fg_color="blue").pack(pady=20)

    def guardar_nota_auto(self, estudiante_id, nota_var, obs_var, estado_label, puntos_maximos=None):
        """Guarda nota automáticamente validando que no exceda el máximo de la evaluación"""
        try:
            puntos_str = nota_var.get().strip()
            
            if not puntos_str:
                estado_label.configure(text="-", text_color="gray")
                if hasattr(self, 'guardado_status_label'):
                    self.guardado_status_label.configure(text="Estado: Sin cambios", text_color="gray")
                return
            
            puntos_ingresados = float(puntos_str)
            
            # Si no se pasó puntos_maximos, obtenerlo de la evaluación actual
            if puntos_maximos is None:
                evals = self.db.get_evaluaciones(self.current_curso)
                eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
                if not eval_info:
                    estado_label.configure(text="ERR", text_color="red")
                    self.status_label.configure(text="Error: Evaluación no encontrada", text_color="red")
                    return
                puntos_maximos = eval_info[2] 
            
            # Validar que no exceda el máximo
            if puntos_ingresados < 0:
                estado_label.configure(text="ERR", text_color="red")
                self.status_label.configure(text="Error: No puede ser negativo", text_color="red")
                if hasattr(self, 'guardado_status_label'):
                    self.guardado_status_label.configure(text="Estado: Error", text_color="red")
                return
                
            if puntos_ingresados > puntos_maximos:
                estado_label.configure(text="ERR", text_color="red")
                self.status_label.configure(text=f"Error: Máximo {puntos_maximos} puntos", text_color="red")
                if hasattr(self, 'guardado_status_label'):
                    self.guardado_status_label.configure(text="Estado: Error - Excede máximo", text_color="red")
                return
            
            # Guardar los puntos directamente
            self.db.guardar_nota(estudiante_id, self.current_evaluacion, puntos_ingresados, obs_var.get())
            
            estado_label.configure(text="OK", text_color="green")
            self.status_label.configure(text=f"Guardado: {puntos_ingresados}/{puntos_maximos} pts", text_color="green")
            if hasattr(self, 'guardado_status_label'):
                self.guardado_status_label.configure(text="Estado: Guardado", text_color="green")
            
            # Actualizar resumen delay
            self.after(100, self.actualizar_resumen)
            
        except ValueError:
            estado_label.configure(text="ERR", text_color="red")
            self.status_label.configure(text="Error: Ingresa un número válido", text_color="red")
            if hasattr(self, 'guardado_status_label'):
                self.guardado_status_label.configure(text="Estado: Error de formato", text_color="red")

    def refrescar_vista(self):
        if self.current_evaluacion:
            self.load_estudiantes_notas()
            self.status_label.configure(text="Vista actualizada")

    def setup_tab_notas(self):
        # Configurar el grid del tab para que ocupe todo el espacio
        self.tab_notas.grid_columnconfigure(0, weight=1)
        self.tab_notas.grid_rowconfigure(1, weight=1)  # Fila 1 es donde va la lista de estudiantes
        
        # Frame de info arriba (fila 0)
        self.info_frame = CTkFrame(self.tab_notas)
        self.info_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.info_label = CTkLabel(self.info_frame, 
                                  text="Selecciona un curso y evaluacion para comenzar", 
                                  font=ctk.CTkFont(size=14, weight="bold"))
        self.info_label.pack(pady=10)
        
        # Frame para la lista de estudiantes (fila 1) - ESTE DEBE EXPANDIRSE
        self.scroll_frame = CTkScrollableFrame(self.tab_notas, 
                                              label_text="Lista de Estudiantes",
                                              height=600)  # Altura fija grande
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_rowconfigure(0, weight=1)
        
        # Botón refrescar abajo (fila 2)
        self.btn_refrescar = CTkButton(self.tab_notas, 
                                      text="Refrescar Datos", 
                                      command=self.refrescar_vista, 
                                      height=40, 
                                      font=ctk.CTkFont(size=14))
        self.btn_refrescar.grid(row=2, column=0, pady=10)

    def setup_tab_config(self):
        self.tab_config.grid_columnconfigure(0, weight=1)
        self.tab_config.grid_rowconfigure(0, weight=1)
        self.config_text = ctk.CTkTextbox(self.tab_config, wrap="word", font=ctk.CTkFont(size=12))
        self.config_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.config_text.insert("0.0", "Aqui se mostrara la configuracion del curso seleccionado...")
        self.config_text.configure(state="disabled")

    def setup_tab_resumen(self):
        self.tab_resumen.grid_columnconfigure(0, weight=1)
        self.tab_resumen.grid_rowconfigure(0, weight=1)
        self.resumen_text = ctk.CTkTextbox(self.tab_resumen, wrap="word", font=ctk.CTkFont(size=12))
        self.resumen_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.resumen_text.insert("0.0", "Selecciona un curso para ver estadisticas...")
        self.resumen_text.configure(state="disabled")

    def actualizar_config_curso(self):
        if not self.current_curso:
            return
        cursos = self.db.get_cursos()
        curso = next((c for c in cursos if c[0] == self.current_curso), None)
        evals = self.db.get_evaluaciones(self.current_curso)
        total_puntos = sum(e[2] for e in evals)
        
        texto = f"CONFIGURACION DEL CURSO\n"
        texto += f"{'='*50}\n\n"
        texto += f"Nombre: {curso[1]}\n"
        texto += f"Descripcion: {curso[2] or 'Ninguna'}\n\n"
        texto += f"EVALUACIONES ({len(evals)} total, {total_puntos} puntos asignados):\n"
        texto += f"{'-'*50}\n"
        
        if evals:
            for e in evals:
                # e[0]=id, e[1]=nombre, e[2]=puntos_maximos, e[3]=orden, e[4]=fecha
                texto += f"{e[3]}. {e[1]} - Máximo: {e[2]} puntos\n"
            if total_puntos != 100:
                texto += f"\n⚠️ ADVERTENCIA: El total es {total_puntos} puntos, deberia ser 100 puntos\n"
        else:
            texto += "No hay evaluaciones configuradas\n"
        
        estudiantes = self.db.get_estudiantes(self.current_curso)
        texto += f"\n\nESTUDIANTES: {len(estudiantes)}\n"
        
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
        texto += f"{'='*50}\n\n"
        if estudiantes and evals:
            promedios = []
            for est in estudiantes:
                prom, _ = self.db.calcular_promedio(est[0], self.current_curso)
                promedios.append(prom)
            import statistics
            texto += f"PROMEDIO GENERAL (suma de puntos): {statistics.mean(promedios):.2f}/100\n"
            texto += f"Nota máxima: {max(promedios):.2f} | Nota mínima: {min(promedios):.2f}\n"
            texto += f"Nota minima: {min(promedios):.2f}\n"
            texto += f"Mediana: {statistics.median(promedios):.2f}\n"
            texto += f"Desviacion estandar: {statistics.stdev(promedios) if len(promedios) > 1 else 0:.2f}\n\n"
            rangos = {'0-59': 0, '60-69': 0, '70-79': 0, '80-89': 0, '90-100': 0}
            for p in promedios:
                if p < 60: rangos['0-59'] += 1
                elif p < 70: rangos['60-69'] += 1
                elif p < 80: rangos['70-79'] += 1
                elif p < 90: rangos['80-89'] += 1
                else: rangos['90-100'] += 1
            texto += "DISTRIBUCION DE NOTAS:\n"
            for r, c in rangos.items():
                barra = "*" * int(c / len(promedios) * 30) if promedios else ""
                texto += f"{r}: {barra} {c} est.\n"
        else:
            texto += "Agrega evaluaciones y estudiantes para ver estadisticas.\n"
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
        
        # ========== SIDEBAR ==========
        self.sidebar = CTkFrame(self, width=400, corner_radius=0)  
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(0, weight=1)
        
        self.sidebar_scroll = CTkScrollableFrame(self.sidebar, width=380, height=800) 
        self.sidebar_scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.title_label = CTkLabel(self.sidebar_scroll, text="Gestor de Notas", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(0, 10))
        
        # --- Frame de Cursos ---
        self.cursos_frame = CTkFrame(self.sidebar_scroll)
        self.cursos_frame.pack(fill="x", pady=5)
        
        CTkLabel(self.cursos_frame, text="Cursos", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.cursos_scroll = CTkScrollableFrame(self.cursos_frame, height=100)
        self.cursos_scroll.pack(fill="x", padx=5, pady=5)
        
        btn_frame = CTkFrame(self.cursos_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=5)
        CTkButton(btn_frame, text="Nuevo", width=80, command=self.crear_curso).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="Editar", width=80, command=self.editar_curso).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="X", width=50, command=self.eliminar_curso, fg_color="red", hover_color="darkred").pack(side="left", padx=2)
        
        # --- Frame de Evaluaciones ---
        self.evals_frame = CTkFrame(self.sidebar_scroll)
        self.evals_frame.pack(fill="x", pady=5)
        
        CTkLabel(self.evals_frame, text="Evaluaciones", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.evals_scroll = CTkScrollableFrame(self.evals_frame, height=100)
        self.evals_scroll.pack(fill="x", padx=5, pady=5)
        
        btn_frame = CTkFrame(self.evals_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=5)
        CTkButton(btn_frame, text="Nuevo", width=60, command=self.agregar_evaluacion).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="Editar", width=60, command=self.editar_evaluacion).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="Rubrica", width=60, command=self.editar_rubrica, fg_color="purple", hover_color="darkpurple").pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="X", width=40, command=self.eliminar_evaluacion, fg_color="orange", hover_color="darkorange").pack(side="left", padx=2)
        
        # --- Frame de Estudiantes ---
        self.est_frame = CTkFrame(self.sidebar_scroll)
        self.est_frame.pack(fill="x", pady=5)
        
        CTkLabel(self.est_frame, text="Estudiantes", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        CTkButton(self.est_frame, text="Agregar Estudiante", command=self.agregar_estudiante).pack(pady=2, fill="x", padx=5)
        CTkButton(self.est_frame, text="Agregar Varios", command=self.agregar_varios_estudiantes).pack(pady=2, fill="x", padx=5)
        
        btn_frame = CTkFrame(self.est_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=2)
        CTkButton(btn_frame, text="Editar", command=self.editar_estudiante).pack(side="left", fill="x", expand=True, padx=2)
        CTkButton(btn_frame, text="Eliminar", command=self.eliminar_estudiante, fg_color="red", hover_color="darkred").pack(side="left", fill="x", expand=True, padx=2)
        
       # --- Frame de Herramientas ---
        self.tools_frame = CTkFrame(self.sidebar_scroll)
        self.tools_frame.pack(fill="x", pady=5)
        
        CTkLabel(self.tools_frame, text="Herramientas", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        CTkButton(self.tools_frame, text="Exportar a Excel", command=self.exportar_excel).pack(pady=2, fill="x", padx=5)
        # NUEVO: Sincronizacion por archivo compartido
        CTkButton(self.tools_frame, text="Sincronizar datos", 
                 command=self.sincronizar_manual, 
                 fg_color="green", hover_color="darkgreen").pack(pady=2, fill="x", padx=10)
        
        # --- Label de Estado ---
        self.status_label = CTkLabel(self.sidebar_scroll, text="Estado: Listo", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=10)
        
        # ========== MAIN FRAME ==========
        self.main_frame = CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # --- Tabview ---
        self.tabview = CTkTabview(self.main_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew")
        
        self.tab_notas = self.tabview.add("Registro de Notas")
        self.tab_clases = self.tabview.add("Control de Clases")
        self.tab_config = self.tabview.add("Configuracion del Curso")
        self.tab_resumen = self.tabview.add("Resumen y Estadisticas")
        
        self.setup_tab_notas()
        self.setup_tab_clases()
        self.setup_tab_config()
        self.setup_tab_resumen()


    def setup_tab_clases(self):
        """Configura la pestaña de Control de Clases con scroll"""
        self.tab_clases.grid_columnconfigure(0, weight=3)
        self.tab_clases.grid_columnconfigure(1, weight=1)
        self.tab_clases.grid_rowconfigure(0, weight=1)
        
        # FRAME SCROLLABLE PRINCIPAL para todo el contenido
        scroll_principal = CTkScrollableFrame(self.tab_clases)
        scroll_principal.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scroll_principal.grid_columnconfigure(0, weight=1)
        
        # ========== CONTENIDO DE LA CLASE ==========
        self.clases_content_frame = CTkFrame(scroll_principal)
        self.clases_content_frame.pack(fill="x", padx=5, pady=5)
        self.clases_content_frame.grid_columnconfigure(0, weight=1)
        
        # --- Fecha de la clase (selector discreto) ---
        fecha_row = CTkFrame(self.clases_content_frame, fg_color="transparent")
        fecha_row.pack(fill="x", padx=10, pady=(10, 5))
        
        CTkLabel(fecha_row, text="📅 Fecha:", 
                font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        
        # Variable para almacenar la fecha (formato DD/MM/AAAA)
        self.fecha_clase_var = ctk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        
        # Botón que muestra la fecha y abre el calendario
        self.btn_fecha_clase = CTkButton(fecha_row, 
                                        text=self.fecha_clase_var.get(),
                                        width=120,
                                        height=32,
                                        command=self.abrir_selector_fecha,
                                        fg_color="blue",
                                        hover_color="darkblue",
                                        font=ctk.CTkFont(size=12))
        self.btn_fecha_clase.pack(side="left")
        
        # Botón para ir a "hoy" - FUNCIÓN DEFINIDA ANTES DE USARLA
        def poner_fecha_hoy():
            hoy = date.today().strftime("%d/%m/%Y")
            self.fecha_clase_var.set(hoy)
            self.btn_fecha_clase.configure(text=hoy)

        CTkButton(fecha_row, text="Hoy", width=60, height=32,
                command=poner_fecha_hoy,
                fg_color="gray").pack(side="left", padx=5)
        
        # --- Selector de Grupo ---
        grupo_row = CTkFrame(self.clases_content_frame, fg_color="transparent")
        grupo_row.pack(fill="x", padx=10, pady=(5, 10))
        
        CTkLabel(grupo_row, text="👥 Grupo:", 
                font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        
        self.grupo_clase_var = ctk.StringVar(value="1")
        def cambiar_grupo(nuevo_grupo):
            self.lbl_info_grupo_clase.configure(text=f"Clases para Grupo {nuevo_grupo}")
            self.cargar_lista_clases()  # Recargar lista filtrada por grupo

        self.combo_grupo_clase = CTkOptionMenu(grupo_row, 
                                            values=["1", "2", "3", "4", "5"],
                                            variable=self.grupo_clase_var,
                                            width=80,
                                            command=cambiar_grupo)
        self.combo_grupo_clase.pack(side="left")
        
        # Label que muestra info del grupo
        self.lbl_info_grupo_clase = CTkLabel(grupo_row, 
                                            text="Clases para Grupo 1",
                                            font=ctk.CTkFont(size=11),
                                            text_color="gray")
        self.lbl_info_grupo_clase.pack(side="left", padx=15)
        
        # --- Encabezado de la clase ---
        CTkLabel(self.clases_content_frame, text="Título de la Clase:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        
        self.entry_encabezado_clase = CTkEntry(self.clases_content_frame, 
                                               placeholder_text="Ej: Clase 1 - Introducción al curso",
                                               height=35, font=ctk.CTkFont(size=14))
        self.entry_encabezado_clase.pack(fill="x", padx=10, pady=5)
        
        # --- Tópicos por tratar ---
        CTkLabel(self.clases_content_frame, text="Topicos que se trataran:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        
        self.entry_topicos = CTkEntry(self.clases_content_frame, 
                                     placeholder_text="Ej: 1. Presentacion del curso, 2. Conceptos basicos, 3. Dinamica grupal...",
                                     height=35)
        self.entry_topicos.pack(fill="x", padx=10, pady=5)
        
        # --- Enlaces de lecturas ---
        CTkLabel(self.clases_content_frame, text="Enlaces de Lecturas Asignadas:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        
        self.frame_links = CTkFrame(self.clases_content_frame)
        self.frame_links.pack(fill="x", padx=10, pady=5)
        
        self.links_entries = []
        
        CTkButton(self.clases_content_frame, text="Agregar Enlace", 
                 command=self.agregar_campo_link, fg_color="blue").pack(pady=5, padx=10, anchor="w")
        
        self.agregar_campo_link()
        
        # --- Contenido/Notas de la clase ---
        CTkLabel(self.clases_content_frame, text="Desarrollo de la Clase (Notas):", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        
        toolbar_frame = CTkFrame(self.clases_content_frame, fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=10, pady=2)
        
        CTkButton(toolbar_frame, text="Negrita", width=80, 
                 command=lambda: self.aplicar_formato_texto("bold")).pack(side="left", padx=2)
        CTkButton(toolbar_frame, text="Cursiva", width=80, 
                 command=lambda: self.aplicar_formato_texto("italic")).pack(side="left", padx=2)
        CTkButton(toolbar_frame, text="Subrayado", width=80, 
                 command=lambda: self.aplicar_formato_texto("underline")).pack(side="left", padx=2)
        
        # Frame contenedor para el Text nativo con scrollbar
        text_container = CTkFrame(self.clases_content_frame)
        text_container.pack(fill="x", padx=10, pady=5)
        text_container.grid_columnconfigure(0, weight=1)
        text_container.grid_rowconfigure(0, weight=1)
        
        # Usar Text nativo de tkinter que soporta tags de formato
        self.texto_clase = tk.Text(text_container, wrap="word", 
                                  font=("Segoe UI", 12), 
                                  height=15,
                                  bg="#2b2b2b",
                                  fg="white",
                                  insertbackground="white",
                                  relief="flat",
                                  borderwidth=0)
        self.texto_clase.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar personalizada
        scrollbar = ctk.CTkScrollbar(text_container, command=self.texto_clase.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.texto_clase.configure(yscrollcommand=scrollbar.set)
        
        # --- Observaciones/Recordatorios ---
        CTkLabel(self.clases_content_frame, text="Observaciones / Recordatorios:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        
        self.entry_observaciones = CTkEntry(self.clases_content_frame, 
                                           placeholder_text="Ej: Traer material para proxima clase, recordar tarea, etc.",
                                           height=50)
        self.entry_observaciones.pack(fill="x", padx=10, pady=5)
        
        # --- Botones de guardar y exportar ---
        btn_frame = CTkFrame(self.clases_content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=15)
        
        CTkButton(btn_frame, text="Guardar Clase", command=self.guardar_clase,
                 fg_color="green", height=40).pack(side="left", padx=5, fill="x", expand=True)
        CTkButton(btn_frame, text="Exportar esta clase a PDF", command=self.exportar_clase_pdf,
                 fg_color="blue", height=40).pack(side="left", padx=5, fill="x", expand=True)
        CTkButton(btn_frame, text="Exportar TODAS las clases", command=self.exportar_todas_clases_pdf,
                 fg_color="purple", height=40).pack(side="left", padx=5, fill="x", expand=True)
        
        # ========== PANEL DERECHO: Herramientas ==========
        self.clases_tools_frame = CTkFrame(self.tab_clases)
        self.clases_tools_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # --- Selector de clase existente ---
        CTkLabel(self.clases_tools_frame, text="Clases Guardadas", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5), padx=10)
        
        self.combo_clases_guardadas = CTkOptionMenu(self.clases_tools_frame, 
                                                    values=["-- Nueva Clase --"],
                                                    command=self.cargar_clase_guardada)
        self.combo_clases_guardadas.pack(fill="x", padx=10, pady=5)
        
        # Botón de actualizar lista
        CTkButton(self.clases_tools_frame, text="Actualizar Lista", 
                 command=self.cargar_lista_clases, fg_color="gray").pack(pady=2, padx=10, fill="x")
        
        CTkButton(self.clases_tools_frame, text="Eliminar Clase Seleccionada", 
                 command=self.eliminar_clase_guardada, fg_color="red").pack(pady=5, padx=10, fill="x")
        
        CTkFrame(self.clases_tools_frame, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)
        
        # --- Botón de Asistencia ---
        CTkLabel(self.clases_tools_frame, text="Control de Asistencia", 
                font=ctk.CTkFont(weight="bold")).pack(pady=5, padx=10)
        
        CTkButton(self.clases_tools_frame, text="Registrar Asistencia", 
                 command=self.abrir_asistencia, height=50, fg_color="orange",
                 font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, padx=10, fill="x")
        
        CTkFrame(self.clases_tools_frame, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)
        
        
        # --- Estado ---
        self.status_clases_label = CTkLabel(self.clases_tools_frame, 
                                             text="Estado: Listo", 
                                             font=ctk.CTkFont(size=12))
        self.status_clases_label.pack(pady=20)
                
        # Bindings para guardado automático
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
        frame_link = CTkFrame(self.frame_links)
        frame_link.pack(fill="x", pady=2)
        entry_nombre = CTkEntry(frame_link, placeholder_text="Nombre del documento/lectura", width=200)
        entry_nombre.pack(side="left", padx=2)
        entry_url = CTkEntry(frame_link, placeholder_text="https://...", width=300)
        entry_url.pack(side="left", padx=2, fill="x", expand=True)
        btn_abrir = CTkButton(frame_link, text="Abrir", width=60, command=lambda: self.abrir_link(entry_url.get()))
        btn_abrir.pack(side="left", padx=2)
        btn_eliminar = CTkButton(frame_link, text="X", width=30, fg_color="red", command=lambda: frame_link.destroy())
        btn_eliminar.pack(side="left", padx=2)
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
            # Obtener rango de selección
            if self.texto_clase.tag_ranges("sel"):
                inicio = self.texto_clase.index("sel.first")
                fin = self.texto_clase.index("sel.last")
                
                # Configurar el tag si no existe
                if tipo == "bold":
                    self.texto_clase.tag_configure("bold", font=("Segoe UI", 12, "bold"))
                    # Toggle: si ya tiene el tag, quitarlo; si no, agregarlo
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
            # No hay selección
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
        
        # Obtener fecha del calendario
        fecha_clase = self.fecha_clase_var.get()
        grupo_clase = self.get_grupo_clase_actual()
        
        encabezado = self.entry_encabezado_clase.get().strip()
        topicos = self.entry_topicos.get().strip()
        observaciones = self.entry_observaciones.get().strip()
        contenido = self.texto_clase.get("1.0", "end").strip()
        
        # Recopilar enlaces
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
        
        # Si no hay encabezado, usar uno por defecto con fecha
        if not encabezado:
            from datetime import datetime
            encabezado = f"Clase del {datetime.now().strftime('%d/%m/%Y')}"
            self.entry_encabezado_clase.delete(0, "end")
            self.entry_encabezado_clase.insert(0, encabezado)
        
        # Determinar si es nueva clase o actualización
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
                # Actualizar clase existente CON FECHA
                success, error = self.db.actualizar_clase(
                    self.clase_actual_id,
                    encabezado=encabezado,
                    grupo=grupo_clase,  # NUEVO
                    topicos=topicos,
                    contenido=contenido,
                    observaciones=observaciones,
                    fecha_clase=fecha_clase
                )
                if not success:
                    raise Exception(error)
                # Eliminar enlaces antiguos y agregar nuevos
                self.db.eliminar_links_clase(self.clase_actual_id)
            
            # Guardar enlaces
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
        # Si no hay curso seleccionado, limpiar el combo
        if not self.current_curso:
            valores = ["-- Nueva Clase --"]
            self.clases_dict = {"-- Nueva Clase --": None}
            if hasattr(self, 'combo_clases_guardadas') and self.combo_clases_guardadas.winfo_exists():
                self.combo_clases_guardadas.configure(values=valores)
                self.combo_clases_guardadas.set("-- Nueva Clase --")
            return
        
        # Obtener clases del grupo seleccionado
        grupo_actual = self.get_grupo_clase_actual()
        clases_db = self.db.get_clases(self.current_curso, grupo=grupo_actual)
        
        # INICIALIZAR variables antes del bucle
        valores = ["-- Nueva Clase --"]
        self.clases_dict = {"-- Nueva Clase --": None}
        
        for clase in clases_db:
            # clase = (id, grupo, encabezado, topicos, contenido, observaciones, fecha_clase, fecha_modificacion)
            clase_id = clase[0]
            grupo = clase[1]
            encabezado = clase[2]
            fecha_clase = clase[6]
            
            # Mostrar fecha y grupo junto al encabezado
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
        
        # Obtener datos de la base de datos
        clase_data = self.db.get_clase_por_id(clase_id)
        
        if not clase_data:
            messagebox.showerror("Error", "No se pudo cargar la clase")
            return
        
        self.clase_actual_id = clase_id
        
        # Cargar campos de forma segura
        try:

            # Cargar grupo en el selector
            grupo_guardado = clase_data.get("grupo", 1)
            self.grupo_clase_var.set(str(grupo_guardado))
            self.lbl_info_grupo_clase.configure(text=f"Clases para Grupo {grupo_guardado}")
            
            self.entry_encabezado_clase.delete(0, "end")
            self.entry_encabezado_clase.insert(0, clase_data.get("encabezado", ""))

            # Cargar fecha en el selector discreto
            fecha_guardada = clase_data.get("fecha_clase")
            if fecha_guardada:
                self.fecha_clase_var.set(fecha_guardada)
                self.btn_fecha_clase.configure(text=fecha_guardada)
            else:
                # Si no hay fecha, poner hoy
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
            
            # Limpiar y recrear links
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
        
        # Confirmar eliminación
        if messagebox.askyesno("Confirmar", f"¿Eliminar permanentemente la clase '{seleccion}'?\n\nEsta acción no se puede deshacer."):
            try:
                success, error = self.db.eliminar_clase(clase_id)
                if success:
                    messagebox.showinfo("Éxito", "Clase eliminada correctamente")
                    self.status_clases_label.configure(text="Clase eliminada")
                    # Limpiar campos y recargar lista
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

         # Resetear fecha a hoy
        hoy = date.today().strftime("%d/%m/%Y")
        self.fecha_clase_var.set(hoy)
        self.btn_fecha_clase.configure(text=hoy)

        # Resetear grupo a 1
        self.grupo_clase_var.set("1")
        self.lbl_info_grupo_clase.configure(text="Clases para Grupo 1")
        
        # Limpiar links
        for widget in self.frame_links.winfo_children():
            widget.destroy()
        self.links_entries = []
        self.agregar_campo_link()  # Agregar al menos un campo vacío
        
        self.status_clases_label.configure(text="Nueva clase")
        self.clase_actual_id = None

    def abrir_selector_fecha(self):
        """Abre un calendario emergente para seleccionar la fecha"""
        popup = CTkToplevel(self)
        popup.title("Seleccionar Fecha")
        popup.geometry("300x300")
        popup.transient(self)
        popup.grab_set()
        
        # Centrar
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (300 // 2)
        y = (popup.winfo_screenheight() // 2) - (300 // 2)
        popup.geometry(f"300x300+{x}+{y}")
        
        CTkLabel(popup, text="Selecciona la fecha:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        # Parsear fecha ACTUALMENTE SELECCIONADA (no la de hoy)
        from datetime import datetime
        try:
            fecha_str = self.fecha_clase_var.get()
            fecha_actual = datetime.strptime(fecha_str, "%d/%m/%Y")
            year, month, day = fecha_actual.year, fecha_actual.month, fecha_actual.day
        except:
            # Si hay error, usar hoy
            hoy = date.today()
            year, month, day = hoy.year, hoy.month, hoy.day
        
        # Calendario compacto
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
        """Abre el diálogo de registro de asistencia con calendario"""
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        # Crear ventana de asistencia
        dialog = ctk.CTkToplevel(self)
        dialog.title("Registro de Asistencia")
        dialog.geometry("900x700")
        dialog.transient(self)
        dialog.grab_set()
        
        # Centrar ventana
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (dialog.winfo_screenheight() // 2) - (700 // 2)
        dialog.geometry(f"900x700+{x}+{y}")
        
        # Frame principal dividido en dos columnas
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_columnconfigure(1, weight=2)
        dialog.grid_rowconfigure(0, weight=1)
        
        # ========== PANEL IZQUIERDO: Calendario y controles ==========
        left_frame = CTkFrame(dialog)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_frame.grid_rowconfigure(5, weight=1)
        
        CTkLabel(left_frame, text="Control de Asistencia", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        CTkLabel(left_frame, text="Seleccionar Fecha:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        
        # ========== SELECTOR DE GRUPO ==========
        grupo_frame = CTkFrame(left_frame, fg_color="transparent")
        grupo_frame.pack(pady=10, fill="x", padx=10)
        
        CTkLabel(grupo_frame, text="Grupo:", 
                font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        
        # Usar el mismo grupo que está en Control de Clases
        self.grupo_asistencia_var = ctk.StringVar(value=self.grupo_clase_var.get())
        
        combo_grupo_asistencia = CTkOptionMenu(grupo_frame, 
                                            values=["1", "2", "3", "4", "5"],
                                            variable=self.grupo_asistencia_var,
                                            width=80,
                                            command=lambda x: [self.cargar_estudiantes_asistencia(cal.get_date()), self.guardar_asistencia_auto()])
        combo_grupo_asistencia.pack(side="left", padx=5)
        
        CTkFrame(left_frame, height=2, fg_color="gray").pack(fill="x", padx=10, pady=5)
        
        # Calendario visual - USAR FECHA DE CONTROL DE CLASES
        cal_frame = CTkFrame(left_frame)
        cal_frame.pack(pady=5, padx=10)
        
        # Parsear la fecha que está en Control de Clases
        from datetime import datetime
        try:
            fecha_inicial = datetime.strptime(self.fecha_clase_var.get(), "%d/%m/%Y")
            year, month, day = fecha_inicial.year, fecha_inicial.month, fecha_inicial.day
        except:
            hoy = date.today()
            year, month, day = hoy.year, hoy.month, hoy.day
        
        cal = Calendar(cal_frame, selectmode='day', 
                    year=year, month=month, day=day,
                    locale='es_ES', font="Arial 10", 
                    background='blue', foreground='white',
                    selectbackground='red', selectforeground='yellow')
        cal.pack(pady=5)
        
        # Mostrar fecha seleccionada
        fecha_label = CTkLabel(left_frame, text=f"Fecha: {cal.get_date()}", 
                            font=ctk.CTkFont(size=14, weight="bold"))
        fecha_label.pack(pady=10)
        
        # Botones de acción rápida
        btn_frame = CTkFrame(left_frame, fg_color="transparent")
        btn_frame.pack(pady=10, fill="x", padx=10)
        
        CTkButton(btn_frame, text="✓ Todos Presentes", 
                command=lambda: [self.marcar_todos_asistencia("presente"), self.guardar_asistencia_auto()],
                fg_color="green", height=35).pack(pady=2, fill="x")
        CTkButton(btn_frame, text="✗ Todos Ausentes", 
                command=lambda: [self.marcar_todos_asistencia("ausente"), self.guardar_asistencia_auto()],
                fg_color="red", height=35).pack(pady=2, fill="x")
        CTkButton(btn_frame, text="Limpiar Todo", 
                command=lambda: [self.marcar_todos_asistencia("sin_marcar"), self.guardar_asistencia_auto()],
                fg_color="gray", height=35).pack(pady=2, fill="x")
        
        # Botón cerrar (el guardado es automático)
        CTkButton(left_frame, text="💾 Cerrar (Guardado automático)", 
                command=lambda: [self.guardar_asistencia_auto(), dialog.destroy()],
                fg_color="blue", height=50, 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20, fill="x", padx=10)
        
        # Estadísticas del día
        self.stats_label = CTkLabel(left_frame, text="Estadísticas: -", 
                                font=ctk.CTkFont(size=12))
        self.stats_label.pack(pady=10)
        
        # ========== PANEL DERECHO: Lista de estudiantes ==========
        right_frame = CTkFrame(dialog)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        
        CTkLabel(right_frame, text="👥 Lista de Estudiantes", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        CTkLabel(right_frame, text="Haz clic en el estado para cambiar (se guarda automáticamente)", 
                font=ctk.CTkFont(size=11), text_color="gray").pack()
        
        # Scrollable frame para estudiantes
        self.asistencia_scroll = CTkScrollableFrame(right_frame, 
                                                label_text="Marcar asistencia",
                                                height=550)
        self.asistencia_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Diccionario para almacenar las variables de estado
        self.checkboxes_asistencia = {}
        
        # Variable para guardar referencia al calendario
        self.cal_asistencia = cal
        
        # Cargar estudiantes inicialmente
        self.cargar_estudiantes_asistencia(cal.get_date())
        
        # Actualizar al cambiar fecha en calendario
        def on_fecha_change(event=None):
            # Guardar asistencia anterior antes de cambiar
            self.guardar_asistencia_auto()
            # Cargar nueva fecha
            self.cargar_estudiantes_asistencia(cal.get_date())
            fecha_label.configure(text=f"Fecha: {cal.get_date()}")
            # Sincronizar con Control de Clases
            self.fecha_clase_var.set(cal.get_date())
            self.btn_fecha_clase.configure(text=cal.get_date())
        
        cal.bind("<<CalendarSelected>>", on_fecha_change)
        
        # Guardar al cerrar la ventana
        def on_closing():
            self.guardar_asistencia_auto()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_closing)

    def cargar_estudiantes_asistencia(self, fecha_str):
        """Carga la lista de estudiantes con toggle simple, mostrando datos guardados"""
        # Limpiar frame anterior
        for widget in self.asistencia_scroll.winfo_children():
            widget.destroy()
        self.checkboxes_asistencia = {}
        
        # Obtener estudiantes del GRUPO seleccionado
        try:
            grupo_asistencia = int(self.grupo_asistencia_var.get())
        except:
            grupo_asistencia = 1
        
        estudiantes = self.db.get_estudiantes(self.current_curso, grupo=grupo_asistencia)
        
        if not estudiantes:
            CTkLabel(self.asistencia_scroll, 
                    text=f"No hay estudiantes en el Grupo {grupo_asistencia}",
                    font=ctk.CTkFont(size=14)).pack(pady=20)
            return
        
        # Cargar asistencia previa del GRUPO y FECHA específicos
        asistencia_previa = self.db.get_asistencia_fecha(self.current_curso, grupo_asistencia, fecha_str)
        
        # Header de columnas
        header = CTkFrame(self.asistencia_scroll)
        header.pack(fill="x", padx=5, pady=5)
        CTkLabel(header, text="Estudiante", font=ctk.CTkFont(weight="bold"), width=300).pack(side="left", padx=5)
        CTkLabel(header, text="Estado (clic para cambiar)", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=20)
        
        CTkFrame(self.asistencia_scroll, height=2, fg_color="gray").pack(fill="x", padx=5, pady=2)
        
        # Función para actualizar estadísticas
        def actualizar_stats():
            presentes = sum(1 for d in self.checkboxes_asistencia.values() if d['estado'] == "presente")
            ausentes = sum(1 for d in self.checkboxes_asistencia.values() if d['estado'] == "ausente")
            total = len(self.checkboxes_asistencia)
            
            if hasattr(self, 'stats_label'):
                self.stats_label.configure(
                    text=f"Presentes: {presentes} | Ausentes: {ausentes} | Total: {total}"
                )
        
        self.actualizar_stats_asistencia = actualizar_stats
        
        # Crear fila para cada estudiante
        for est in estudiantes:
            est_id, nombre, grupo, email, carne = est
            est_id_str = str(est_id)
            
            # Frame para cada estudiante
            row = CTkFrame(self.asistencia_scroll)
            row.pack(fill="x", pady=2, padx=5)
            
            # Nombre del estudiante
            nombre_text = f"{nombre}"
            if carne:
                nombre_text += f" ({carne})"
            
            lbl_nombre = CTkLabel(row, text=nombre_text, font=ctk.CTkFont(size=12), width=300)
            lbl_nombre.pack(side="left", padx=5)
            
            # Botón toggle - USA DATOS GUARDADOS si existen
            estado_inicial = asistencia_previa.get(est_id_str, "sin_marcar")
            
            btn_toggle = CTkButton(row, text="SIN MARCAR", width=120, height=32,
                                font=ctk.CTkFont(size=12, weight="bold"))
            btn_toggle.pack(side="right", padx=10)
            
            # Guardar referencia
            self.checkboxes_asistencia[est_id_str] = {
                'estado': estado_inicial,
                'boton': btn_toggle
            }
            
            # Función para actualizar apariencia del botón
            def actualizar_boton(eid=est_id_str):
                datos = self.checkboxes_asistencia[eid]
                estado = datos['estado']
                boton = datos['boton']
                
                if estado == "presente":
                    boton.configure(
                        text="PRESENTE ✓",
                        fg_color="green",
                        hover_color="darkgreen"
                    )
                elif estado == "ausente":
                    boton.configure(
                        text="AUSENTE ✗",
                        fg_color="red",
                        hover_color="darkred"
                    )
                else:
                    boton.configure(
                        text="SIN MARCAR",
                        fg_color="gray",
                        hover_color="darkgray"
                    )
                actualizar_stats()
                # Guardar automáticamente al cambiar
                self.guardar_asistencia_auto()
            
            # Función para toggle
            def toggle_estado(eid=est_id_str):
                datos = self.checkboxes_asistencia[eid]
                # Ciclo: sin_marcar -> presente -> ausente -> sin_marcar
                if datos['estado'] == "sin_marcar":
                    datos['estado'] = "presente"
                elif datos['estado'] == "presente":
                    datos['estado'] = "ausente"
                else:
                    datos['estado'] = "sin_marcar"
                actualizar_boton(eid)
            
            # Configurar comando
            btn_toggle.configure(command=lambda eid=est_id_str: toggle_estado(eid))
            
            # Aplicar estado inicial visual
            actualizar_boton(est_id_str)
        
        # Actualizar estadísticas iniciales
        actualizar_stats()

    def marcar_todos_asistencia(self, estado):
        """Marca todos los estudiantes con el mismo estado"""
        if not hasattr(self, 'checkboxes_asistencia') or not self.checkboxes_asistencia:
            return
        
        for est_id, datos in self.checkboxes_asistencia.items():
            datos['estado'] = estado
            # Actualizar botón
            if estado == "presente":
                datos['boton'].configure(
                    text="PRESENTE ✓",
                    fg_color="green",
                    hover_color="darkgreen"
                )
            elif estado == "ausente":
                datos['boton'].configure(
                    text="AUSENTE ✗",
                    fg_color="red",
                    hover_color="darkred"
                )
            else:
                datos['boton'].configure(
                    text="SIN MARCAR",
                    fg_color="gray",
                    hover_color="darkgray"
                )
        
        # Actualizar estadísticas
        if hasattr(self, 'actualizar_stats_asistencia'):
            self.actualizar_stats_asistencia()
        
        # Guardar automáticamente
        self.guardar_asistencia_auto()

    def guardar_asistencia_db(self, fecha_str, dialog):
        """Guarda el registro de asistencia en la base de datos"""
        if not hasattr(self, 'checkboxes_asistencia') or not self.checkboxes_asistencia:
            messagebox.showwarning("Advertencia", "No hay estudiantes para guardar")
            return
        
        # Recopilar datos de TODOS los estudiantes (tanto presentes como ausentes)
        asistencia_data = {}
        for est_id, datos in self.checkboxes_asistencia.items():
            estado = datos['estado']
            # Guardar tanto presentes como ausentes
            asistencia_data[est_id] = estado
        
        if not asistencia_data:
            messagebox.showwarning("Advertencia", "No hay estudiantes para guardar")
            return
        
        # Obtener grupo y guardar en base de datos
        grupo_asistencia = int(self.grupo_asistencia_var.get())
        
        # Primero eliminar registros existentes para esta fecha/grupo (para permitir cambios)
        success_del, error_del = self.db.eliminar_asistencia_fecha(self.current_curso, grupo_asistencia, fecha_str)
        
        # Luego guardar los nuevos datos
        success, error = self.db.guardar_asistencia(self.current_curso, grupo_asistencia, fecha_str, asistencia_data)
        
        if success:
            # Actualizar estadisticas finales del GRUPO
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
        
        # Recopilar datos
        asistencia_data = {}
        for est_id, datos in self.checkboxes_asistencia.items():
            estado = datos['estado']
            if estado in ["presente", "ausente"]:  # Solo guardar si está marcado
                asistencia_data[est_id] = estado
        
        if not asistencia_data:
            return
        
        # Obtener fecha y grupo
        fecha_str = self.cal_asistencia.get_date() if hasattr(self, 'cal_asistencia') else self.fecha_clase_var.get()
        try:
            grupo_asistencia = int(self.grupo_asistencia_var.get())
        except:
            grupo_asistencia = 1
        
        # Guardar silenciosamente
        try:
            # Primero eliminar registros existentes
            self.db.eliminar_asistencia_fecha(self.current_curso, grupo_asistencia, fecha_str)
            # Luego guardar nuevos
            self.db.guardar_asistencia(self.current_curso, grupo_asistencia, fecha_str, asistencia_data)
            
            # Actualizar estadísticas sin mostrar mensaje
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
        
        # Verificar que los widgets existen
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
        
        # Obtener valores de los campos de forma segura
        try:
            encabezado = self.entry_encabezado_clase.get().strip() if self.entry_encabezado_clase else ""
            topicos = self.entry_topicos.get().strip() if hasattr(self, 'entry_topicos') and self.entry_topicos.winfo_exists() else ""
            observaciones = self.entry_observaciones.get().strip() if hasattr(self, 'entry_observaciones') and self.entry_observaciones.winfo_exists() else ""
            # Para tk.Text usar get con rangos, no get("1.0", "end")
            contenido = self.texto_clase.get("1.0", "end-1c").strip() if hasattr(self, 'texto_clase') else ""
        except Exception as e:
            messagebox.showerror("Error", f"Error al leer los campos: {str(e)}")
            return
        
        if not encabezado:
            encabezado = "Clase sin titulo"
        
        # Pedir ubicación para guardar
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
        
        # Contenedor para elementos
        elementos = []
        
        # Estilos
        estilos = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle(
            'Titulo',
            parent=estilos['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=1  # Centro
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
        
        # TITULO
        elementos.append(Paragraph("REGISTRO DE CLASE", estilo_titulo))
        elementos.append(Spacer(1, 0.2*inch))
        
        # ENCABEZADO
        elementos.append(Paragraph(f"<b>{encabezado}</b>", estilo_subtitulo))
        elementos.append(Spacer(1, 0.1*inch))
        
        # CURSO
        curso_nombre = "Curso no seleccionado"
        if hasattr(self, 'cursos_data'):
            for nombre, cid in self.cursos_data.items():
                if cid == self.current_curso:
                    curso_nombre = nombre
                    break
        
        elementos.append(Paragraph(f"<b>Curso:</b> {curso_nombre}", estilo_normal))
        elementos.append(Paragraph(f"<b>Fecha de exportacion:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_normal))
        elementos.append(Spacer(1, 0.2*inch))
        
        # TOPICOS
        if topicos:
            elementos.append(Paragraph("<b>TOPICOS A TRATAR:</b>", estilo_subtitulo))
            elementos.append(Paragraph(topicos.replace('\n', '<br/>'), estilo_normal))
            elementos.append(Spacer(1, 0.2*inch))
        
        # ENLACES
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
        
        # CONTENIDO DE LA CLASE
        if contenido:
            elementos.append(Paragraph("<b>DESARROLLO DE LA CLASE:</b>", estilo_subtitulo))
            # Convertir saltos de linea a <br/>
            contenido_html = contenido.replace('\n', '<br/>')
            elementos.append(Paragraph(contenido_html, estilo_normal))
            elementos.append(Spacer(1, 0.2*inch))
        
        # OBSERVACIONES
        if observaciones:
            elementos.append(Paragraph("<b>OBSERVACIONES:</b>", estilo_subtitulo))
            elementos.append(Paragraph(observaciones.replace('\n', '<br/>'), estilo_normal))
        
        # Construir PDF
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
        
        # Obtener todas las clases de la base de datos
        clases_db = self.db.get_clases(self.current_curso)
        
        if not clases_db:
            messagebox.showwarning("Advertencia", "No hay clases guardadas para exportar")
            return
        
        # Pedir ubicacion
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
            
            # Estilos
            estilos = getSampleStyleSheet()
            estilo_titulo = ParagraphStyle('Titulo', parent=estilos['Heading1'], fontSize=20, 
                                          textColor=colors.HexColor('#1f4788'), spaceAfter=30, alignment=1)
            estilo_subtitulo = ParagraphStyle('Subtitulo', parent=estilos['Heading2'], fontSize=14,
                                             textColor=colors.HexColor('#2e5c8a'), spaceAfter=12)
            estilo_normal = estilos["BodyText"]
            estilo_normal.fontSize = 11
            
            # Portada
            elementos.append(Spacer(1, 2*inch))
            elementos.append(Paragraph("REGISTRO DE CLASES", estilo_titulo))
            elementos.append(Spacer(1, 0.5*inch))
            elementos.append(Paragraph(f"<b>Curso:</b> {curso_nombre}", estilo_subtitulo))
            elementos.append(Paragraph(f"<b>Total de clases:</b> {len(clases_db)}", estilo_normal))
            elementos.append(Paragraph(f"<b>Fecha de exportacion:</b> {datetime.now().strftime('%d/%m/%Y')}", estilo_normal))
            elementos.append(PageBreak())
            
            # Cada clase
            for idx, clase_row in enumerate(clases_db, 1):
                clase_id = clase_row[0]
                
                # Obtener datos completos de la clase
                clase_data = self.db.get_clase_por_id(clase_id)
                
                if not clase_data:
                    continue
                
                # Numero de clase
                elementos.append(Paragraph(f"CLASE {idx}", estilo_titulo))
                elementos.append(Paragraph(f"<b>{clase_data.get('encabezado', 'Sin titulo')}</b>", estilo_subtitulo))
                
                # Topicos
                topicos = clase_data.get('topicos', '')
                if topicos:
                    elementos.append(Paragraph("<b>Topicos:</b> " + topicos, estilo_normal))
                
                # Enlaces
                links = clase_data.get('links', [])
                if links:
                    elementos.append(Paragraph("<b>Lecturas asignadas:</b>", estilo_normal))
                    for link in links:
                        elementos.append(Paragraph(f"• {link['nombre']}: {link['url']}", estilo_normal))
                
                # Contenido (resumido si es muy largo)
                contenido = clase_data.get('contenido', '')
                if contenido:
                    if len(contenido) > 1000:
                        contenido = contenido[:1000] + "..."
                    elementos.append(Paragraph("<b>Desarrollo:</b><br/>" + contenido.replace('\n', '<br/>'), estilo_normal))
                
                # Observaciones
                obs = clase_data.get('observaciones', '')
                if obs:
                    elementos.append(Paragraph("<b>Observaciones:</b> " + obs, estilo_normal))
                
                elementos.append(Spacer(1, 0.3*inch))
                elementos.append(PageBreak())
            
            # Eliminar el ultimo PageBreak
            if elementos and isinstance(elementos[-1], PageBreak):
                elementos.pop()
            
            doc.build(elementos)
            messagebox.showinfo("Exito", f"PDF con {len(clases_db)} clases guardado:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el PDF:\n{str(e)}")

if __name__ == "__main__":
    app = GestorNotasApp()
    app.mainloop()