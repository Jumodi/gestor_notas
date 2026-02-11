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

SISTEMA = platform.system()

# Funciones para manejar rutas en .exe y en desarrollo

def get_executable_dir():
    """Obtiene la carpeta donde está el .exe o el script"""
    if getattr(sys, 'frozen', False):
        # Si es .exe, devuelve la carpeta del .exe
        return os.path.dirname(sys.executable)
    else:
        # Si es script .py, devuelve la carpeta del script
        return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    """Obtiene la ruta correcta tanto en desarrollo como en .exe"""
    if hasattr(sys, '_MEIPASS'):
        # Si es .exe (PyInstaller crea carpeta temporal)
        base_path = sys._MEIPASS
    else:
        # Si es script .py normal
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_data_path():
    """Obtiene la ruta de la carpeta data (en la misma ubicación que el .exe)"""
    if getattr(sys, 'frozen', False):
        # Si es .exe, data está junto al .exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Si es script, data está en la carpeta del proyecto
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    data_path = os.path.join(base_path, 'data')
    os.makedirs(data_path, exist_ok=True)
    return data_path

def get_token_path():
    """Obtiene la ruta del token.json (junto al .exe, no dentro del .exe)"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, 'token.json')

# Definir rutas globales
DATA_DIR = get_data_path()
DB_PATH = os.path.join(DATA_DIR, 'notas.db')
CREDENTIALS_PATH = os.path.join(get_executable_dir(), 'credentials.json')
TOKEN_PATH = get_token_path()

print(f"DEBUG: Buscando credentials en: {CREDENTIALS_PATH}")  # Línea temporal para verificar
print(f"DEBUG: ¿Existe?: {os.path.exists(CREDENTIALS_PATH)}")  # Línea temporal para verificar


# Detectar sistema operativo
SISTEMA = platform.system()

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class GestorNotasApp(CTk):
    def __init__(self):
        super().__init__()
    
        self.title("Gestor de Evaluaciones Universitarias")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Usar rutas dinámicas para .exe
        self.db = DatabaseManager(DB_PATH)
        self.drive = GoogleDriveSync(credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH)
        self.sync_manager = SyncManager(credentials_path=CREDENTIALS_PATH, token_path=TOKEN_PATH)
        self.current_curso = None
        self.current_evaluacion = None
        self.entries_notas = {}
        self.auto_sync_enabled = False
        
        self.setup_ui()
        self.load_cursos()
        self.setup_auto_sync()

        # Sincronizar datos Drive

    def setup_auto_sync(self):
        """Configura sincronización automática cada 5 minutos"""
        def auto_sync_loop():
            while self.auto_sync_enabled:
                time.sleep(300)  # 5 minutos
                if self.current_curso and os.path.exists(DB_PATH):
                    try:
                        success, msg = self.sync_manager.upload_database(DB_PATH)
                        if success:
                            self.after(0, lambda: self.status_label.configure(text=f"☁️ {msg}"))
                    except:
                        pass  # Silenciar errores en background
        
        self.auto_sync_enabled = True
        threading.Thread(target=auto_sync_loop, daemon=True).start()

    def sincronizar_manual(self):
        """Sincronización manual con opciones"""
        if not os.path.exists(CREDENTIALS_PATH):
            messagebox.showerror("Error", "No se ha configurado Google Drive.\nVe a Configurar Drive primero.")
            return
        
        # Crear diálogo de opciones
        dialog = ctk.CTkToplevel(self)
        dialog.title("Sincronizar con Drive")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        CTkLabel(dialog, text="Opciones de sincronización", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        def subir():
            success, msg = self.sync_manager.upload_database(DB_PATH)
            messagebox.showinfo("Resultado", msg)
            dialog.destroy()
        
        def descargar():
            # Backup antes de descargar
            if os.path.exists(DB_PATH):
                respuesta = messagebox.askyesno("Confirmar", 
                    "Esto reemplazará tu base de datos local.\n¿Deseas continuar?")
                if not respuesta:
                    return
            
            success, msg = self.sync_manager.download_latest(DB_PATH)
            if success:
                messagebox.showinfo("Éxito", msg + "\n\nReinicia la aplicación para ver los cambios.")
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
                texto += f"• {v['fecha']} por {v['user']}\n"
            
            messagebox.showinfo("Versiones", texto)
        
        CTkButton(dialog, text="⬆️ Subir ahora", command=subir, 
                 fg_color="blue").pack(pady=5, fill="x", padx=20)
        CTkButton(dialog, text="⬇️ Descargar última", command=descargar, 
                 fg_color="green").pack(pady=5, fill="x", padx=20)
        CTkButton(dialog, text="📋 Ver versiones", command=ver_versiones, 
                 fg_color="gray").pack(pady=5, fill="x", padx=20)
        
        # Toggle auto-sync
        def toggle_auto():
            self.auto_sync_enabled = not self.auto_sync_enabled
            estado = "ACTIVADA" if self.auto_sync_enabled else "DESACTIVADA"
            btn_auto.configure(text=f"Auto-sync: {estado}")
        
        estado = "ACTIVADA" if self.auto_sync_enabled else "DESACTIVADA"
        btn_auto = CTkButton(dialog, text=f"Auto-sync: {estado}", 
                            command=toggle_auto, fg_color="orange")
        btn_auto.pack(pady=10, fill="x", padx=20)

    def compartir_carpeta(self):
        """Comparte acceso con otro usuario"""
        if not os.path.exists(CREDENTIALS_PATH):
            messagebox.showerror("Error", "Configura Google Drive primero")
            return
        
        dialog = CTkInputDialog(text="Email del colaborador:", title="Compartir acceso")
        email = dialog.get_input()
        
        if email and '@' in email:
            success, msg = self.sync_manager.share_folder(email)
            if success:
                messagebox.showinfo("Éxito", msg)
            else:
                messagebox.showerror("Error", msg)
    
    # ========== FUNCIONES DE CURSOS  ==========
    
    def crear_curso(self):
        dialog = CTkInputDialog(text="Nombre del nuevo curso:", title="Crear Curso")
        nombre = dialog.get_input()
        
        if nombre and nombre.strip():
            nombre = nombre.strip()
            dialog2 = CTkInputDialog(text="Descripción (opcional):", title="Crear Curso")
            descripcion = dialog2.get_input() or ""
            
            curso_id, error = self.db.crear_curso(nombre, descripcion)
            
            if curso_id:
                messagebox.showinfo("Éxito", f"Curso '{nombre}' creado correctamente.\n\nAhora agrega evaluaciones y estudiantes.")
                self.load_cursos()
            else:
                messagebox.showerror("Error", error or "No se pudo crear el curso")
    
    def seleccionar_curso(self, nombre_curso):
        """Selecciona un curso y actualiza la interfaz"""
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
                
                btn_text = f"{nombre}\n({total_est} est, {total_eval} eval)"
                btn = CTkButton(
                    self.cursos_scroll,
                    text=btn_text,
                    command=lambda n=nombre: self.seleccionar_curso(n),
                    fg_color="transparent",
                    border_width=2,
                    border_color="gray",
                    hover_color="gray25",
                    anchor="w"
                )
                btn.pack(fill="x", pady=2, padx=5)
                self.curso_buttons[nombre] = btn
            
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
            
            dialog2 = CTkInputDialog(text="Nueva descripción:", title="Editar Curso")
            dialog2._input.insert(0, curso[2] or "")
            nueva_desc = dialog2.get_input()
            
            success, error = self.db.actualizar_curso(self.current_curso, nuevo_nombre, nueva_desc)
            
            if success:
                messagebox.showinfo("Éxito", "Curso actualizado correctamente")
                self.load_cursos()
            else:
                messagebox.showerror("Error", error or "No se pudo actualizar")
    
    def eliminar_curso(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        # Obtener nombre del curso seleccionado
        curso_nombre = None
        for nombre, cid in self.cursos_data.items():
            if cid == self.current_curso:
                curso_nombre = nombre
                break
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar permanentemente el curso '{curso_nombre}'?\n\nSe perderán TODOS los datos (evaluaciones, estudiantes y notas)."):
            success, error = self.db.eliminar_curso(self.current_curso)
            if success:
                messagebox.showinfo("Éxito", "Curso eliminado correctamente")
                self.current_curso = None
                self.current_evaluacion = None
                self.load_cursos()
                self.limpiar_interfaz()
            else:
                messagebox.showerror("Error", error or "No se pudo eliminar el curso")
    
    # ========== FUNCIONES DE EVALUACIONES ==========
    
    def seleccionar_evaluacion(self, nombre_eval):
        """Selecciona una evaluación y actualiza la interfaz"""
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
        
        for widget in self.evals_scroll.winfo_children():
            widget.destroy()
        
        evals = self.db.get_evaluaciones(self.current_curso)
        self.evals_data = {}
        self.eval_buttons = {}
        
        if evals:
            for eval in evals:
                eval_id, nombre, porcentaje, orden, fecha = eval
                self.evals_data[nombre] = eval_id
                
                btn_text = f"{nombre} ({porcentaje}%)"
                btn = CTkButton(
                    self.evals_scroll,
                    text=btn_text,
                    command=lambda n=nombre: self.seleccionar_evaluacion(n),
                    fg_color="transparent",
                    border_width=2,
                    border_color="gray",
                    hover_color="gray25",
                    anchor="w",
                    height=30
                )
                btn.pack(fill="x", pady=2, padx=5)
                self.eval_buttons[nombre] = btn
            
            self.seleccionar_evaluacion(evals[0][1])
        else:
            CTkLabel(self.evals_scroll, text="Sin evaluaciones").pack(pady=10)
            self.current_evaluacion = None
            self.limpiar_tab_notas()
    
    def agregar_evaluacion(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        dialog = CTkInputDialog(text="Nombre de la evaluación:", title="Nueva Evaluación")
        nombre = dialog.get_input()
        
        if nombre and nombre.strip():
            nombre = nombre.strip()
            
            dialog2 = CTkInputDialog(text="Porcentaje (%):", title="Nueva Evaluación")
            try:
                porcentaje_str = dialog2.get_input()
                porcentaje = float(porcentaje_str) if porcentaje_str else 0
                if porcentaje <= 0 or porcentaje > 100:
                    raise ValueError
            except:
                messagebox.showerror("Error", "Porcentaje inválido. Debe ser entre 1 y 100.")
                return
            
            total_actual = self.db.verificar_porcentaje_total(self.current_curso)
            if total_actual + porcentaje > 100:
                messagebox.showerror("Error", 
                    f"El total de porcentajes sería {total_actual + porcentaje}%.\n"
                    f"El máximo permitido es 100%.\n"
                    f"Porcentaje actual usado: {total_actual}%")
                return
            
            eval_id, error = self.db.agregar_evaluacion(self.current_curso, nombre, porcentaje)
            
            if eval_id:
                messagebox.showinfo("Éxito", f"Evaluación '{nombre}' agregada ({porcentaje}%)")
                self.load_evaluaciones()
                self.actualizar_config_curso()
            else:
                messagebox.showerror("Error", error or "No se pudo agregar la evaluación")
    
    def editar_evaluacion(self):
        if not self.current_evaluacion:
            messagebox.showwarning("Advertencia", "Selecciona una evaluación primero")
            return
        
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_actual = next((e for e in evals if e[0] == self.current_evaluacion), None)
        
        if not eval_actual:
            return
        
        dialog = CTkInputDialog(text="Nuevo nombre de la evaluación:", title="Editar Evaluación")
        dialog._input.insert(0, eval_actual[1])
        nuevo_nombre = dialog.get_input()
        
        if nuevo_nombre and nuevo_nombre.strip():
            nuevo_nombre = nuevo_nombre.strip()
            
            dialog2 = CTkInputDialog(text=f"Nuevo porcentaje (actual: {eval_actual[2]}%):", title="Editar Evaluación")
            dialog2._input.insert(0, str(eval_actual[2]))
            try:
                nuevo_pct = float(dialog2.get_input() or eval_actual[2])
            except:
                nuevo_pct = eval_actual[2]
            
            total_actual = self.db.verificar_porcentaje_total(self.current_curso)
            total_sin_esta = total_actual - eval_actual[2]
            
            if total_sin_esta + nuevo_pct > 100:
                messagebox.showerror("Error", 
                    f"El total sería {total_sin_esta + nuevo_pct}%. Máximo permitido: 100%")
                return
            
            success, error = self.db.actualizar_evaluacion(self.current_evaluacion, nuevo_nombre, nuevo_pct)
            
            if success:
                messagebox.showinfo("Éxito", "Evaluación actualizada")
                self.load_evaluaciones()
                self.actualizar_config_curso()
            else:
                messagebox.showerror("Error", error or "No se pudo actualizar")
    
    def eliminar_evaluacion(self):
        if not self.current_evaluacion:
            messagebox.showwarning("Advertencia", "Selecciona una evaluación primero")
            return
        
        # Obtener nombre de la evaluación seleccionada
        eval_nombre = None
        for nombre, eid in self.evals_data.items():
            if eid == self.current_evaluacion:
                eval_nombre = nombre
                break
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar la evaluación '{eval_nombre}'?\n\nSe perderán las notas asociadas."):
            success, error = self.db.eliminar_evaluacion(self.current_evaluacion)
            if success:
                messagebox.showinfo("Éxito", "Evaluación eliminada")
                self.load_evaluaciones()
                self.actualizar_config_curso()
            else:
                messagebox.showerror("Error", error or "No se pudo eliminar")
    
    # ========== FUNCIONES DE ESTUDIANTES ==========
    
    def agregar_estudiante(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        dialog = CTkInputDialog(text="Nombre completo del estudiante:", title="Nuevo Estudiante")
        nombre = dialog.get_input()
        
        if nombre and nombre.strip():
            nombre = nombre.strip()
            
            dialog2 = CTkInputDialog(text="Grupo (número, 1 por defecto):", title="Nuevo Estudiante")
            try:
                grupo_str = dialog2.get_input()
                grupo = int(grupo_str) if grupo_str else 1
            except:
                grupo = 1
            
            dialog3 = CTkInputDialog(text="Email (opcional):", title="Nuevo Estudiante")
            email = dialog3.get_input() or None
            
            est_id, error = self.db.agregar_estudiante(self.current_curso, nombre, grupo, email)
            
            if est_id:
                messagebox.showinfo("Éxito", f"Estudiante '{nombre}' agregado")
                self.load_estudiantes_notas()
                self.actualizar_resumen()
                self.load_cursos()
            else:
                messagebox.showerror("Error", error or "No se pudo agregar el estudiante")
    
    def agregar_varios_estudiantes(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Agregar Varios Estudiantes")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        CTkLabel(dialog, text="Ingresa los nombres (uno por línea):", 
                font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        text_box = ctk.CTkTextbox(dialog, width=450, height=250)
        text_box.pack(pady=10, padx=20)
        
        def guardar():
            nombres = text_box.get("1.0", "end").strip().split("\n")
            nombres = [n.strip() for n in nombres if n.strip()]
            
            agregados = 0
            for nombre in nombres:
                est_id, _ = self.db.agregar_estudiante(self.current_curso, nombre, 1, None)
                if est_id:
                    agregados += 1
            
            messagebox.showinfo("Éxito", f"{agregados} estudiantes agregados")
            dialog.destroy()
            self.load_estudiantes_notas()
            self.actualizar_resumen()
            self.load_cursos()
        
        CTkButton(dialog, text="Agregar Todos", command=guardar, 
                 fg_color="green", hover_color="darkgreen").pack(pady=10)
    
    def editar_estudiante(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        estudiantes = self.db.get_estudiantes(self.current_curso)
        if not estudiantes:
            messagebox.showinfo("Info", "No hay estudiantes en este curso")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar Estudiante")
        dialog.geometry("400x400")
        dialog.transient(self)
        dialog.grab_set()
        
        CTkLabel(dialog, text="Selecciona estudiante a editar:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        nombres = [f"{e[1]} (G{e[2]})" for e in estudiantes]
        est_var = ctk.StringVar(value=nombres[0])
        menu = CTkOptionMenu(dialog, values=nombres, variable=est_var, width=350)
        menu.pack(pady=10)
        
        def abrir_edicion():
            seleccion = est_var.get()
            idx = nombres.index(seleccion)
            est = estudiantes[idx]
            est_id, nombre_actual, grupo_actual, email_actual = est
            
            dialog.destroy()
            
            edit_dialog = ctk.CTkToplevel(self)
            edit_dialog.title(f"Editar: {nombre_actual}")
            edit_dialog.geometry("400x350")
            edit_dialog.transient(self)
            edit_dialog.grab_set()
            
            CTkLabel(edit_dialog, text="Nombre:").pack(pady=(10,0))
            entry_nombre = CTkEntry(edit_dialog, width=350)
            entry_nombre.insert(0, nombre_actual)
            entry_nombre.pack(pady=5)
            
            CTkLabel(edit_dialog, text="Grupo:").pack(pady=(10,0))
            entry_grupo = CTkEntry(edit_dialog, width=350)
            entry_grupo.insert(0, str(grupo_actual))
            entry_grupo.pack(pady=5)
            
            CTkLabel(edit_dialog, text="Email:").pack(pady=(10,0))
            entry_email = CTkEntry(edit_dialog, width=350)
            entry_email.insert(0, email_actual or "")
            entry_email.pack(pady=5)
            
            def guardar_cambios():
                nuevo_nombre = entry_nombre.get().strip() or nombre_actual
                try:
                    nuevo_grupo = int(entry_grupo.get()) or grupo_actual
                except:
                    nuevo_grupo = grupo_actual
                nuevo_email = entry_email.get().strip() or None
                
                success, error = self.db.actualizar_estudiante(
                    est_id, nuevo_nombre, nuevo_grupo, nuevo_email
                )
                
                if success:
                    messagebox.showinfo("Éxito", "Estudiante actualizado")
                    edit_dialog.destroy()
                    self.load_estudiantes_notas()
                    self.actualizar_resumen()
                    self.load_cursos()
                else:
                    messagebox.showerror("Error", error or "No se pudo actualizar")
            
            CTkButton(edit_dialog, text="💾 Guardar Cambios", 
                     command=guardar_cambios, fg_color="green", hover_color="darkgreen").pack(pady=20)
        
        CTkButton(dialog, text="✏️ Editar Seleccionado", command=abrir_edicion).pack(pady=20)
    
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
        
        CTkLabel(dialog, text="Selecciona estudiante a eliminar:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        est_var = ctk.StringVar(value=nombres[0])
        menu = CTkOptionMenu(dialog, values=nombres, variable=est_var, width=350)
        menu.pack(pady=10)
        
        def confirmar():
            seleccion = est_var.get()
            est_id = int(seleccion.split("(ID:")[1].replace(")", ""))
            nombre = seleccion.split(" (ID:")[0]
            
            if messagebox.askyesno("Confirmar", f"¿Eliminar a '{nombre}' permanentemente?"):
                success, _ = self.db.eliminar_estudiante(est_id)
                if success:
                    messagebox.showinfo("Éxito", "Estudiante eliminado")
                    dialog.destroy()
                    self.load_estudiantes_notas()
                    self.actualizar_resumen()
                    self.load_cursos()
        
        CTkButton(dialog, text="Eliminar", command=confirmar, 
                 fg_color="red", hover_color="darkred").pack(pady=20)
    
    # ========== PESTAÑA DE NOTAS ==========
    
    def load_estudiantes_notas(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        self.entries_notas = {}
        
        if not self.current_curso:
            CTkLabel(self.scroll_frame, text="⚠️ Selecciona un curso primero", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
            return
        
        if not self.current_evaluacion:
            CTkLabel(self.scroll_frame, text="⚠️ Selecciona una evaluación primero", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
            return
        
        estudiantes = self.db.get_estudiantes(self.current_curso)
        
        if not estudiantes:
            CTkLabel(self.scroll_frame, text="📋 No hay estudiantes en este curso.\n\nAgrega estudiantes usando el botón '➕ Agregar Estudiante' en el menú lateral.", 
                    font=ctk.CTkFont(size=12)).pack(pady=20)
            return
        
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
        
        if eval_info:
            eval_nombre = eval_info[1]
            eval_porcentaje = eval_info[2]
        else:
            eval_nombre = "Evaluación"
            eval_porcentaje = 0
        
        header_info = CTkFrame(self.scroll_frame)
        header_info.pack(fill="x", padx=5, pady=5)
        
        CTkLabel(header_info, 
                text=f"📝 Evaluación: {eval_nombre} ({eval_porcentaje}%) - Guardado automático", 
                font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        header = CTkFrame(self.scroll_frame)
        header.pack(fill="x", padx=5, pady=2)
        
        CTkLabel(header, text="Estudiante", font=ctk.CTkFont(weight="bold"), width=350).pack(side="left", padx=10)
        CTkLabel(header, text="Nota", font=ctk.CTkFont(weight="bold"), width=150).pack(side="left", padx=10)
        CTkLabel(header, text="Observaciones", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, fill="x", expand=True)
        
        for est in estudiantes:
            est_id, nombre, grupo, email = est
            
            row = CTkFrame(self.scroll_frame)
            row.pack(fill="x", padx=5, pady=2)
            
            nombre_text = f"{nombre}" + (f" (G{grupo})" if grupo > 1 else "")
            CTkLabel(row, text=nombre_text, width=350).pack(side="left", padx=10)
            
            nota_existente, obs_existente = self.db.get_nota(est_id, self.current_evaluacion)
            
            nota_frame = CTkFrame(row, fg_color="transparent")
            nota_frame.pack(side="left", padx=5)
            
            nota_var = ctk.StringVar(value=str(nota_existente) if nota_existente is not None else "")
            entry_nota = CTkEntry(nota_frame, width=80, textvariable=nota_var, justify="center", 
                                 placeholder_text="0-100")
            entry_nota.pack(side="left")
            
            estado_text = "✓" if nota_existente else "○"
            estado_color = "green" if nota_existente else "gray"
            estado_label = CTkLabel(nota_frame, text=estado_text, width=25, text_color=estado_color)
            estado_label.pack(side="left", padx=(5, 0))
            
            obs_var = ctk.StringVar(value=obs_existente or "")
            entry_obs = CTkEntry(row, textvariable=obs_var, 
                                placeholder_text="Observaciones...")
            entry_obs.pack(side="left", padx=10, fill="x", expand=True)
            
            def guardar_al_salir(event, eid=est_id, nv=nota_var, ov=obs_var, el=estado_label):
                self.guardar_nota_auto(eid, nv, ov, el)
            
            entry_nota.bind("<FocusOut>", guardar_al_salir)
            entry_obs.bind("<FocusOut>", guardar_al_salir)
            entry_nota.bind("<Return>", guardar_al_salir)
            entry_obs.bind("<Return>", guardar_al_salir)
            
            self.entries_notas[est_id] = (nota_var, obs_var, estado_label)
        
        self.status_label.configure(text=f"📊 {len(estudiantes)} estudiantes - Guardado automático activo")
    
    def guardar_nota_auto(self, estudiante_id, nota_var, obs_var, estado_label):
        """Guarda nota automáticamente al cambiar de campo"""
        try:
            nota_str = nota_var.get().strip()
            
            if not nota_str:
                estado_label.configure(text="○", text_color="gray")
                return
            
            nota = float(nota_str)
            if not 0 <= nota <= 100:
                estado_label.configure(text="❌", text_color="red")
                self.status_label.configure(text="❌ Nota debe ser entre 0-100", text_color="red")
                return
            
            self.db.guardar_nota(estudiante_id, self.current_evaluacion, nota, obs_var.get())
            
            estado_label.configure(text="✓", text_color="green")
            self.status_label.configure(text=f"✅ Nota guardada", text_color="green")
            
            self.after(100, self.actualizar_resumen)
            
        except ValueError:
            estado_label.configure(text="❌", text_color="red")
            self.status_label.configure(text="❌ Error: Ingresa un número válido", text_color="red")
    
    def refrescar_vista(self):
        """Recarga la vista actual"""
        if self.current_evaluacion:
            self.load_estudiantes_notas()
            self.status_label.configure(text="🔄 Vista actualizada")
    
    # ========== PESTAÑAS Y CONFIGURACIÓN ==========
    
    def setup_tab_notas(self):
        self.tab_notas.grid_columnconfigure(0, weight=1)
        self.tab_notas.grid_rowconfigure(1, weight=1)
        
        self.info_frame = CTkFrame(self.tab_notas)
        self.info_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.info_label = CTkLabel(self.info_frame, text="Selecciona un curso y evaluación para comenzar", 
                                  font=ctk.CTkFont(size=14, weight="bold"))
        self.info_label.pack(pady=10)
        
        self.scroll_frame = CTkScrollableFrame(self.tab_notas, label_text="Lista de Estudiantes")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        self.btn_refrescar = CTkButton(self.tab_notas, text="🔄 Refrescar Datos", 
                                      command=self.refrescar_vista,
                                      height=40, font=ctk.CTkFont(size=14))
        self.btn_refrescar.grid(row=2, column=0, pady=10)
    
    def setup_tab_config(self):
        self.tab_config.grid_columnconfigure(0, weight=1)
        self.tab_config.grid_rowconfigure(0, weight=1)
        
        self.config_text = ctk.CTkTextbox(self.tab_config, wrap="word", font=ctk.CTkFont(size=12))
        self.config_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.config_text.insert("0.0", "Aquí se mostrará la configuración del curso seleccionado...")
        self.config_text.configure(state="disabled")
    
    def setup_tab_resumen(self):
        self.tab_resumen.grid_columnconfigure(0, weight=1)
        self.tab_resumen.grid_rowconfigure(0, weight=1)
        
        self.resumen_text = ctk.CTkTextbox(self.tab_resumen, wrap="word", font=ctk.CTkFont(size=12))
        self.resumen_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.resumen_text.insert("0.0", "Selecciona un curso para ver estadísticas...")
        self.resumen_text.configure(state="disabled")
    
    def actualizar_config_curso(self):
        if not self.current_curso:
            return
        
        cursos = self.db.get_cursos()
        curso = next((c for c in cursos if c[0] == self.current_curso), None)
        evals = self.db.get_evaluaciones(self.current_curso)
        
        total_porcentaje = sum(e[2] for e in evals)
        
        texto = f"⚙️ CONFIGURACIÓN DEL CURSO\n"
        texto += f"{'='*50}\n\n"
        texto += f"Nombre: {curso[1]}\n"
        texto += f"Descripción: {curso[2] or 'Ninguna'}\n\n"
        
        texto += f"📋 EVALUACIONES ({len(evals)} total, {total_porcentaje}% asignado):\n"
        texto += f"{'-'*50}\n"
        
        if evals:
            for e in evals:
                texto += f"{e[3]}. {e[1]} - {e[2]}%\n"
            if total_porcentaje != 100:
                texto += f"\n⚠️ ADVERTENCIA: El total es {total_porcentaje}%, debería ser 100%\n"
        else:
            texto += "No hay evaluaciones configuradas\n"
        
        estudiantes = self.db.get_estudiantes(self.current_curso)
        texto += f"\n\n👥 ESTUDIANTES: {len(estudiantes)}\n"
        
        grupos = {}
        for e in estudiantes:
            grupos[e[2]] = grupos.get(e[2], 0) + 1
        
        for g, count in sorted(grupos.items()):
            texto += f"  Grupo {g}: {count} estudiantes\n"
        
        self.config_text.configure(state="normal")
        self.config_text.delete("0.0", "end")
        self.config_text.insert("0.0", texto)
        self.config_text.configure(state="disabled")
    
    def actualizar_resumen(self):
        if not self.current_curso:
            return
        
        cursos = self.db.get_cursos()
        curso = next((c for c in cursos if c[0] == self.current_curso), None)
        evals = self.db.get_evaluaciones(self.current_curso)
        estudiantes = self.db.get_estudiantes(self.current_curso)
        
        texto = f"📊 RESUMEN: {curso[1]}\n"
        texto += f"{'='*50}\n\n"
        
        if estudiantes and evals:
            promedios = []
            for est in estudiantes:
                prom, _ = self.db.calcular_promedio(est[0], self.current_curso)
                promedios.append(prom)
            
            import statistics
            texto += f"Promedio general del curso: {statistics.mean(promedios):.2f}\n"
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
            
            texto += "📈 DISTRIBUCIÓN DE NOTAS:\n"
            for r, c in rangos.items():
                barra = "█" * int(c / len(promedios) * 30) if promedios else ""
                texto += f"{r}: {barra} {c} est.\n"
        else:
            texto += "Agrega evaluaciones y estudiantes para ver estadísticas.\n"
        
        self.resumen_text.configure(state="normal")
        self.resumen_text.delete("0.0", "end")
        self.resumen_text.insert("0.0", texto)
        self.resumen_text.configure(state="disabled")
    
    def actualizar_info_curso(self):
        if self.current_curso:
            # Buscar el nombre del curso actual
            for nombre, cid in self.cursos_data.items():
                if cid == self.current_curso:
                    self.info_label.configure(text=f"Curso: {nombre}")
                    return
        else:
            self.info_label.configure(text="Selecciona un curso y evaluación para comenzar")
    
    def limpiar_interfaz(self):
        self.info_label.configure(text="Selecciona un curso y evaluación para comenzar")
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
        CTkLabel(self.scroll_frame, text="Selecciona un curso y una evaluación para ver los estudiantes", 
                font=ctk.CTkFont(size=12)).pack(pady=20)
    
    # ========== HERRAMIENTAS ==========
    
    def exportar_excel(self):
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        # Obtener nombre del curso
        nombre_archivo = "curso"
        for nombre, cid in self.cursos_data.items():
            if cid == self.current_curso:
                nombre_archivo = nombre.replace(" ", "_")
                break
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"notas_{nombre_archivo}.xlsx"
        )
        
        if filepath:
            try:
                self.db.exportar_a_excel(self.current_curso, filepath)
                self.status_label.configure(text=f"✅ Exportado")
                messagebox.showinfo("Éxito", f"Archivo guardado:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar:\n{str(e)}")
    
    def sincronizar_drive(self):
        if not os.path.exists(CREDENTIALS_PATH):
            messagebox.showerror("Error", "No se encontró credentials.json\nConfigura Google Drive primero.")
            return
        
        self.status_label.configure(text="☁️ Sincronizando...")
        self.update()
        
        def sync_task():
            success, msg = self.drive.sincronizar_db(DB_PATH)
            self.after(0, lambda: self.sync_completed(success, msg))
        
        thread = threading.Thread(target=sync_task)
        thread.start()
    
    def sync_completed(self, success, msg):
        if success:
            self.status_label.configure(text=f"✅ Sincronizado")
            messagebox.showinfo("Éxito", "Base de datos sincronizada con Google Drive")
        else:
            self.status_label.configure(text=f"❌ Error")
            messagebox.showerror("Error", msg)
    
    def configurar_drive(self):
        instrucciones = """
Para configurar Google Drive:

1. Ve a https://console.cloud.google.com/  
2. Crea un nuevo proyecto
3. Habilita la API de Google Drive
4. Ve a "Credenciales" → "Crear credenciales" → "ID de cliente OAuth"
5. Configura la pantalla de consentimiento (Externo)
6. Agrega tu email como usuario de prueba
7. Descarga el archivo JSON y guárdalo como 'credentials.json' en esta carpeta

¿Deseas abrir la consola de Google Cloud ahora?
        """
        
        if messagebox.askyesno("Configurar Google Drive", instrucciones):
            import webbrowser
            webbrowser.open("https://console.cloud.google.com/  ")
    
    # ========== SETUP_UI ==========
    
    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ========== SIDEBAR CON SCROLL ==========
        self.sidebar = CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(0, weight=1)  # El scroll ocupa todo el espacio
        
        # Scrollable frame para todo el contenido del sidebar
        self.sidebar_scroll = CTkScrollableFrame(self.sidebar, width=280, height=800)
        self.sidebar_scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Título
        self.title_label = CTkLabel(self.sidebar_scroll, text="📚 Gestor de Notas", 
                                   font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(0, 10))
        
        # ========== GESTIÓN DE CURSOS ==========
        self.cursos_frame = CTkFrame(self.sidebar_scroll)
        self.cursos_frame.pack(fill="x", pady=5)
        
        CTkLabel(self.cursos_frame, text="Cursos", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Frame scrollable para botones de cursos
        self.cursos_scroll = CTkScrollableFrame(self.cursos_frame, height=100)
        self.cursos_scroll.pack(fill="x", padx=5, pady=5)
        
        btn_frame = CTkFrame(self.cursos_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        CTkButton(btn_frame, text="➕ Nuevo", width=80, 
                 command=self.crear_curso).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="✏️ Editar", width=80, 
                 command=self.editar_curso).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="❌", width=50, 
                 command=self.eliminar_curso, fg_color="red", hover_color="darkred").pack(side="left", padx=2)
        
        # ========== GESTIÓN DE EVALUACIONES ==========
        self.evals_frame = CTkFrame(self.sidebar_scroll)
        self.evals_frame.pack(fill="x", pady=5)
        
        CTkLabel(self.evals_frame, text="Evaluaciones", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Frame scrollable para botones de evaluaciones
        self.evals_scroll = CTkScrollableFrame(self.evals_frame, height=100)
        self.evals_scroll.pack(fill="x", padx=5, pady=5)
        
        btn_frame = CTkFrame(self.evals_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        CTkButton(btn_frame, text="➕ Nuevo", width=80, 
                 command=self.agregar_evaluacion).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="✏️ Editar", width=80, 
                 command=self.editar_evaluacion).pack(side="left", padx=2, fill="x", expand=True)
        CTkButton(btn_frame, text="❌", width=50, 
                 command=self.eliminar_evaluacion, fg_color="orange", hover_color="darkorange").pack(side="left", padx=2)
        
        # ========== GESTIÓN DE ESTUDIANTES ==========
        self.est_frame = CTkFrame(self.sidebar_scroll)
        self.est_frame.pack(fill="x", pady=5)
        
        CTkLabel(self.est_frame, text="Estudiantes", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        CTkButton(self.est_frame, text="➕ Agregar Estudiante", 
                 command=self.agregar_estudiante).pack(pady=2, fill="x", padx=5)
        CTkButton(self.est_frame, text="➕ Agregar Varios", 
                 command=self.agregar_varios_estudiantes).pack(pady=2, fill="x", padx=5)
        
        btn_frame = CTkFrame(self.est_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=2)
        
        CTkButton(btn_frame, text="✏️ Editar", 
                 command=self.editar_estudiante).pack(side="left", fill="x", expand=True, padx=2)
        CTkButton(btn_frame, text="❌ Eliminar", 
                 command=self.eliminar_estudiante, fg_color="red", hover_color="darkred").pack(side="left", fill="x", expand=True, padx=2)
        
        # ========== HERRAMIENTAS (AHORA VISIBLE CON SCROLL) ==========
        self.tools_frame = CTkFrame(self.sidebar_scroll)
        self.tools_frame.pack(fill="x", pady=5)
        
        CTkLabel(self.tools_frame, text="Herramientas", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        CTkButton(self.tools_frame, text="📊 Exportar a Excel", 
                  command=self.exportar_excel).pack(pady=2, fill="x", padx=5)
        CTkButton(self.tools_frame, text="⚙️ Configurar Drive", 
                  command=self.configurar_drive).pack(pady=2, fill="x", padx=10)
        CTkButton(self.tools_frame, text="☁️ Sincronizar", 
                  command=self.sincronizar_manual, 
                  fg_color="green", 
                  hover_color="darkgreen").pack(pady=2, fill="x", padx=10)
        CTkButton(self.tools_frame, text="👤 Compartir acceso", 
                  command=self.compartir_carpeta, 
                  fg_color="blue", 
                  hover_color="darkblue").pack(pady=2, fill="x", padx=10)
        
        # Status (al final del scroll)
        self.status_label = CTkLabel(self.sidebar_scroll, text="Estado: Listo", 
                                    font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=10)
        
        # ========== ÁREA PRINCIPAL ==========
        self.main_frame = CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        self.tabview = CTkTabview(self.main_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew")
        
        self.tab_notas = self.tabview.add("Registro de Notas")
        self.tab_config = self.tabview.add("Configuración del Curso")
        self.tab_resumen = self.tabview.add("Resumen y Estadísticas")
        
        self.setup_tab_notas()
        self.setup_tab_config()
        self.setup_tab_resumen()

if __name__ == "__main__":
    app = GestorNotasApp()
    app.mainloop()