import customtkinter as ctk
from customtkinter import CTk, CTkFrame, CTkLabel, CTkButton, CTkOptionMenu, CTkEntry, CTkScrollableFrame, CTkTabview, CTkInputDialog, CTkToplevel
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from database import DatabaseManager
from drive_sync import GoogleDriveSync
import os
import threading
import platform
from sync_manager import SyncManager
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
        self.drive = GoogleDriveSync(credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH)
        self.sync_manager = SyncManager(credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH)
        self.current_curso = None
        self.current_evaluacion = None
        self.entries_notas = {}
        self.auto_sync_enabled = False
        self.clase_actual_id = None
        self.setup_ui()
        self.load_cursos()
        self.setup_auto_sync()

    def setup_auto_sync(self):
        def auto_sync_loop():
            while self.auto_sync_enabled:
                time.sleep(300)
                if self.current_curso and os.path.exists(DB_PATH):
                    try:
                        success, msg = self.sync_manager.upload_database(DB_PATH)
                        if success:
                            self.after(0, lambda: self.status_label.configure(text=f"Sync: {msg}"))
                    except:
                        pass
        self.auto_sync_enabled = True
        threading.Thread(target=auto_sync_loop, daemon=True).start()

    def sincronizar_manual(self):
        if not os.path.exists(CREDENTIALS_PATH):
            messagebox.showerror("Error", "No se ha configurado Google Drive. Ve a Configurar Drive primero.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Sincronizar con Drive")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        CTkLabel(dialog, text="Opciones de sincronizacion", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        def subir():
            success, msg = self.sync_manager.upload_database(DB_PATH)
            messagebox.showinfo("Resultado", msg)
            dialog.destroy()
        def descargar():
            if os.path.exists(DB_PATH):
                respuesta = messagebox.askyesno("Confirmar", "Esto reemplazara tu base de datos local. Deseas continuar?")
                if not respuesta:
                    return
            success, msg = self.sync_manager.download_latest(DB_PATH)
            if success:
                messagebox.showinfo("Exito", msg + "\n\nReinicia la aplicacion para ver los cambios.")
                self.load_cursos()
            else:
                messagebox.showerror("Error", msg)
            dialog.destroy()
        def ver_versiones():
            versions = self.sync_manager.list_versions(limit=10)
            if not versions:
                messagebox.showinfo("Versiones", "No hay versiones en Drive")
                return
            texto = "Versiones disponibles:\n\n"
            for v in versions[:5]:
                texto += f"- {v['fecha']} por {v['user']}\n"
            messagebox.showinfo("Versiones", texto)
        CTkButton(dialog, text="Subir ahora", command=subir, fg_color="blue").pack(pady=5, fill="x", padx=20)
        CTkButton(dialog, text="Descargar ultima", command=descargar, fg_color="green").pack(pady=5, fill="x", padx=20)
        CTkButton(dialog, text="Ver versiones", command=ver_versiones, fg_color="gray").pack(pady=5, fill="x", padx=20)
        def toggle_auto():
            self.auto_sync_enabled = not self.auto_sync_enabled
            estado = "ACTIVADA" if self.auto_sync_enabled else "DESACTIVADA"
            btn_auto.configure(text=f"Auto-sync: {estado}")
        estado = "ACTIVADA" if self.auto_sync_enabled else "DESACTIVADA"
        btn_auto = CTkButton(dialog, text=f"Auto-sync: {estado}", command=toggle_auto, fg_color="orange")
        btn_auto.pack(pady=10, fill="x", padx=20)

    def compartir_carpeta(self):
        if not os.path.exists(CREDENTIALS_PATH):
            messagebox.showerror("Error", "Configura Google Drive primero")
            return
        dialog = CTkInputDialog(text="Email del colaborador:", title="Compartir acceso")
        email = dialog.get_input()
        if email and '@' in email:
            success, msg = self.sync_manager.share_folder(email)
            if success:
                messagebox.showinfo("Exito", msg)
            else:
                messagebox.showerror("Error", msg)

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
                                 text=f"👤 {nombre}", 
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
            
            nota_container = CTkFrame(row, fg_color="transparent")
            nota_container.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            
            nota_var = ctk.StringVar(value=str(nota_existente) if nota_existente is not None else "")
            entry_nota = CTkEntry(nota_container, width=80, textvariable=nota_var, 
                     justify="center", placeholder_text=f"0-{puntos_max}")
            entry_nota.pack(side="left", padx=2)
            
            estado_text = "✓" if nota_existente else "-"
            estado_color = "green" if nota_existente else "gray"
            estado_label = CTkLabel(nota_container, text=estado_text, width=20, 
                                   text_color=estado_color, font=ctk.CTkFont(size=12, weight="bold"))
            estado_label.pack(side="left", padx=2)
            
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
        """Muestra modal con datos del estudiante al hacer clic"""
        est_id, nombre, grupo, email, carne = estudiante
        
        modal = CTkToplevel(self)
        modal.title(f"Datos del Estudiante")
        modal.geometry("400x300")
        modal.transient(self)
        modal.grab_set()
        
        # Centrar en pantalla
        modal.update_idletasks()
        x = (modal.winfo_screenwidth() // 2) - (400 // 2)
        y = (modal.winfo_screenheight() // 2) - (300 // 2)
        modal.geometry(f"400x300+{x}+{y}")
        
        # Contenido
        CTkLabel(modal, text="👤", font=ctk.CTkFont(size=48)).pack(pady=(20, 10))
        CTkLabel(modal, text=nombre, font=ctk.CTkFont(size=18, weight="bold")).pack()
        
        frame_datos = CTkFrame(modal)
        frame_datos.pack(fill="x", padx=30, pady=20)
        
        # Grupo
        CTkLabel(frame_datos, text="Grupo:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        CTkLabel(frame_datos, text=str(grupo)).grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Carné
        CTkLabel(frame_datos, text="Carné:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        CTkLabel(frame_datos, text=carne or "No registrado").grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Email
        CTkLabel(frame_datos, text="Email:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        email_text = email or "No registrado"
        CTkLabel(frame_datos, text=email_text).grid(row=2, column=1, sticky="w", padx=10, pady=5)
        
        # Botón cerrar
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

    def sincronizar_drive(self):
        if not os.path.exists(CREDENTIALS_PATH):
            messagebox.showerror("Error", "No se encontro credentials.json. Configura Google Drive primero.")
            return
        self.status_label.configure(text="Sincronizando...")
        self.update()
        def sync_task():
            success, msg = self.drive.sincronizar_db(DB_PATH)
            self.after(0, lambda: self.sync_completed(success, msg))
        thread = threading.Thread(target=sync_task)
        thread.start()

    def sync_completed(self, success, msg):
        if success:
            self.status_label.configure(text="Sincronizado")
            messagebox.showinfo("Exito", "Base de datos sincronizada con Google Drive")
        else:
            self.status_label.configure(text="Error")
            messagebox.showerror("Error", msg)

    def configurar_drive(self):
        instrucciones = """Para configurar Google Drive:

1. Ve a https://console.cloud.google.com/
2. Crea un nuevo proyecto
3. Habilita la API de Google Drive
4. Ve a "Credenciales" -> "Crear credenciales" -> "ID de cliente OAuth"
5. Configura la pantalla de consentimiento (Externo)
6. Agrega tu email como usuario de prueba
7. Descarga el archivo JSON y guardalo como 'credentials.json' en esta carpeta

Deseas abrir la consola de Google Cloud ahora?"""
        if messagebox.askyesno("Configurar Google Drive", instrucciones):
            import webbrowser
            webbrowser.open("https://console.cloud.google.com/")

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = CTkFrame(self, width=400, corner_radius=0)  
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar_scroll = CTkScrollableFrame(self.sidebar, width=380, height=800) 
        self.sidebar_scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.title_label = CTkLabel(self.sidebar_scroll, text="Gestor de Notas", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(0, 10))
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
        self.evals_frame = CTkFrame(self.sidebar_scroll)
        self.evals_frame.pack(fill="x", pady=5)
        CTkLabel(self.evals_frame, text="Evaluaciones", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.evals_scroll = CTkScrollableFrame(self.evals_frame, height=100)
        self.evals_scroll.pack(fill="x", padx=5, pady=5)
        btn_frame = CTkFrame(self.evals_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=5)
        CTkButton(btn_frame, text="Nuevo", width=80, command=self.agregar_evaluacion).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="Editar", width=80, command=self.editar_evaluacion).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="X", width=50, command=self.eliminar_evaluacion, fg_color="orange", hover_color="darkorange").pack(side="left", padx=2)
        self.est_frame = CTkFrame(self.sidebar_scroll)
        self.est_frame.pack(fill="x", pady=5)
        CTkLabel(self.est_frame, text="Estudiantes", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        CTkButton(self.est_frame, text="Agregar Estudiante", command=self.agregar_estudiante).pack(pady=2, fill="x", padx=5)
        CTkButton(self.est_frame, text="Agregar Varios", command=self.agregar_varios_estudiantes).pack(pady=2, fill="x", padx=5)
        btn_frame = CTkFrame(self.est_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=2)
        CTkButton(btn_frame, text="Editar", command=self.editar_estudiante).pack(side="left", fill="x", expand=True, padx=2)
        CTkButton(btn_frame, text="Eliminar", command=self.eliminar_estudiante, fg_color="red", hover_color="darkred").pack(side="left", fill="x", expand=True, padx=2)
        self.tools_frame = CTkFrame(self.sidebar_scroll)
        self.tools_frame.pack(fill="x", pady=5)
        CTkLabel(self.tools_frame, text="Herramientas", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        CTkButton(self.tools_frame, text="Exportar a Excel", command=self.exportar_excel).pack(pady=2, fill="x", padx=5)
        CTkButton(self.tools_frame, text="Configurar Drive", command=self.configurar_drive).pack(pady=2, fill="x", padx=10)
        CTkButton(self.tools_frame, text="Sincronizar", command=self.sincronizar_manual, fg_color="green", hover_color="darkgreen").pack(pady=2, fill="x", padx=10)
        CTkButton(self.tools_frame, text="Compartir acceso", command=self.compartir_carpeta, fg_color="blue", hover_color="darkblue").pack(pady=2, fill="x", padx=10)
        self.status_label = CTkLabel(self.sidebar_scroll, text="Estado: Listo", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=10)
        self.main_frame = CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
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