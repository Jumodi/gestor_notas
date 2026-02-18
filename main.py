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
                btn = CTkButton(self.cursos_scroll, text=btn_text, command=lambda n=nombre: self.seleccionar_curso(n), fg_color="transparent", border_width=2, border_color="gray", hover_color="gray25", anchor="w")
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
                btn = CTkButton(self.evals_scroll, text=btn_text, command=lambda n=nombre: self.seleccionar_evaluacion(n), fg_color="transparent", border_width=2, border_color="gray", hover_color="gray25", anchor="w", height=30)
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
                messagebox.showerror("Error", f"El total de porcentajes seria {total_actual + porcentaje}%. El maximo permitido es 100%. Porcentaje actual usado: {total_actual}%")
                return
            eval_id, error = self.db.agregar_evaluacion(self.current_curso, nombre, porcentaje)
            if eval_id:
                messagebox.showinfo("Exito", f"Evaluacion '{nombre}' agregada ({porcentaje}%)")
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
        dialog = CTkInputDialog(text="Nombre completo del estudiante:", title="Nuevo Estudiante")
        nombre = dialog.get_input()
        if nombre and nombre.strip():
            nombre = nombre.strip()
            dialog2 = CTkInputDialog(text="Grupo (numero, 1 por defecto):", title="Nuevo Estudiante")
            try:
                grupo_str = dialog2.get_input()
                grupo = int(grupo_str) if grupo_str else 1
            except:
                grupo = 1
            dialog3 = CTkInputDialog(text="Email (opcional):", title="Nuevo Estudiante")
            email = dialog3.get_input() or None
            est_id, error = self.db.agregar_estudiante(self.current_curso, nombre, grupo, email)
            if est_id:
                messagebox.showinfo("Exito", f"Estudiante '{nombre}' agregado")
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
        CTkLabel(dialog, text="Ingresa los nombres (uno por linea):", font=ctk.CTkFont(weight="bold")).pack(pady=10)
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
            messagebox.showinfo("Exito", f"{agregados} estudiantes agregados")
            dialog.destroy()
            self.load_estudiantes_notas()
            self.actualizar_resumen()
            self.load_cursos()
        CTkButton(dialog, text="Agregar Todos", command=guardar, fg_color="green", hover_color="darkgreen").pack(pady=10)

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
        CTkLabel(dialog, text="Selecciona estudiante a editar:", font=ctk.CTkFont(weight="bold")).pack(pady=10)
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
                success, error = self.db.actualizar_estudiante(est_id, nuevo_nombre, nuevo_grupo, nuevo_email)
                if success:
                    messagebox.showinfo("Exito", "Estudiante actualizado")
                    edit_dialog.destroy()
                    self.load_estudiantes_notas()
                    self.actualizar_resumen()
                    self.load_cursos()
                else:
                    messagebox.showerror("Error", error or "No se pudo actualizar")
            CTkButton(edit_dialog, text="Guardar Cambios", command=guardar_cambios, fg_color="green", hover_color="darkgreen").pack(pady=20)
        CTkButton(dialog, text="Editar Seleccionado", command=abrir_edicion).pack(pady=20)

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
            CTkLabel(self.scroll_frame, text="Selecciona un curso primero", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
            return
        if not self.current_evaluacion:
            CTkLabel(self.scroll_frame, text="Selecciona una evaluacion primero", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
            return
        estudiantes = self.db.get_estudiantes(self.current_curso)
        if not estudiantes:
            CTkLabel(self.scroll_frame, text="No hay estudiantes en este curso. Agrega estudiantes usando el boton Agregar Estudiante en el menu lateral.", font=ctk.CTkFont(size=12)).pack(pady=20)
            return
        evals = self.db.get_evaluaciones(self.current_curso)
        eval_info = next((e for e in evals if e[0] == self.current_evaluacion), None)
        if eval_info:
            eval_nombre = eval_info[1]
            eval_porcentaje = eval_info[2]
        else:
            eval_nombre = "Evaluacion"
            eval_porcentaje = 0
        header_info = CTkFrame(self.scroll_frame)
        header_info.pack(fill="x", padx=5, pady=5)
        CTkLabel(header_info, text=f"Evaluacion: {eval_nombre} ({eval_porcentaje}%) - Guardado automatico", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        header = CTkFrame(self.scroll_frame)
        header.pack(fill="x", padx=5, pady=2)
        header.grid_columnconfigure(0, weight=0, minsize=350)
        header.grid_columnconfigure(1, weight=0, minsize=120)
        header.grid_columnconfigure(2, weight=1)
        CTkLabel(header, text="Estudiante", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        CTkLabel(header, text="Nota", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        CTkLabel(header, text="Observaciones", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=(5, 10), pady=5, sticky="w")
        for est in estudiantes:
            est_id, nombre, grupo, email = est
            row = CTkFrame(self.scroll_frame)
            row.pack(fill="x", padx=5, pady=2)
            row.grid_columnconfigure(0, weight=0, minsize=350)
            row.grid_columnconfigure(1, weight=0, minsize=120)
            row.grid_columnconfigure(2, weight=1)
            nombre_text = f"{nombre}" + (f" (G{grupo})" if grupo > 1 else "")
            CTkLabel(row, text=nombre_text).grid(row=0, column=0, padx=(10, 5), pady=2, sticky="w")
            nota_existente, obs_existente = self.db.get_nota(est_id, self.current_evaluacion)
            nota_container = CTkFrame(row, fg_color="transparent", width=120, height=30)
            nota_container.grid(row=0, column=1, padx=5, pady=2, sticky="nsew")
            nota_container.grid_propagate(False)
            nota_var = ctk.StringVar(value=str(nota_existente) if nota_existente is not None else "")
            entry_nota = CTkEntry(nota_container, width=70, textvariable=nota_var, justify="center", placeholder_text="0-100")
            entry_nota.place(relx=0.35, rely=0.5, anchor="center")
            estado_text = "OK" if nota_existente else "-"
            estado_color = "green" if nota_existente else "gray"
            estado_label = CTkLabel(nota_container, text=estado_text, width=20, text_color=estado_color, font=ctk.CTkFont(size=14, weight="bold"))
            estado_label.place(relx=0.85, rely=0.5, anchor="center")
            obs_var = ctk.StringVar(value=obs_existente or "")
            entry_obs = CTkEntry(row, textvariable=obs_var, placeholder_text="Observaciones...")
            entry_obs.grid(row=0, column=2, padx=(5, 10), pady=2, sticky="ew")
            def guardar_al_salir(event, eid=est_id, nv=nota_var, ov=obs_var, el=estado_label):
                self.guardar_nota_auto(eid, nv, ov, el)
            entry_nota.bind("<FocusOut>", guardar_al_salir)
            entry_obs.bind("<FocusOut>", guardar_al_salir)
            entry_nota.bind("<Return>", guardar_al_salir)
            entry_obs.bind("<Return>", guardar_al_salir)
            self.entries_notas[est_id] = (nota_var, obs_var, estado_label)
        self.status_label.configure(text=f"{len(estudiantes)} estudiantes - Guardado automatico activo")

    def guardar_nota_auto(self, estudiante_id, nota_var, obs_var, estado_label):
        try:
            nota_str = nota_var.get().strip()
            if not nota_str:
                estado_label.configure(text="-", text_color="gray")
                return
            nota = float(nota_str)
            if not 0 <= nota <= 100:
                estado_label.configure(text="ERR", text_color="red")
                self.status_label.configure(text="Error: Nota debe ser entre 0-100", text_color="red")
                return
            self.db.guardar_nota(estudiante_id, self.current_evaluacion, nota, obs_var.get())
            estado_label.configure(text="OK", text_color="green")
            self.status_label.configure(text="Nota guardada", text_color="green")
            self.after(100, self.actualizar_resumen)
        except ValueError:
            estado_label.configure(text="ERR", text_color="red")
            self.status_label.configure(text="Error: Ingresa un numero valido", text_color="red")

    def refrescar_vista(self):
        if self.current_evaluacion:
            self.load_estudiantes_notas()
            self.status_label.configure(text="Vista actualizada")

    def setup_tab_notas(self):
        self.tab_notas.grid_columnconfigure(0, weight=1)
        self.tab_notas.grid_rowconfigure(1, weight=1)
        self.info_frame = CTkFrame(self.tab_notas)
        self.info_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.info_label = CTkLabel(self.info_frame, text="Selecciona un curso y evaluacion para comenzar", font=ctk.CTkFont(size=14, weight="bold"))
        self.info_label.pack(pady=10)
        self.scroll_frame = CTkScrollableFrame(self.tab_notas, label_text="Lista de Estudiantes")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.btn_refrescar = CTkButton(self.tab_notas, text="Refrescar Datos", command=self.refrescar_vista, height=40, font=ctk.CTkFont(size=14))
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
        total_porcentaje = sum(e[2] for e in evals)
        texto = f"CONFIGURACION DEL CURSO\n"
        texto += f"{'='*50}\n\n"
        texto += f"Nombre: {curso[1]}\n"
        texto += f"Descripcion: {curso[2] or 'Ninguna'}\n\n"
        texto += f"EVALUACIONES ({len(evals)} total, {total_porcentaje}% asignado):\n"
        texto += f"{'-'*50}\n"
        if evals:
            for e in evals:
                texto += f"{e[3]}. {e[1]} - {e[2]}%\n"
            if total_porcentaje != 100:
                texto += f"\nADVERTENCIA: El total es {total_porcentaje}%, deberia ser 100%\n"
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
            texto += f"Promedio general del curso: {statistics.mean(promedios):.2f}\n"
            texto += f"Nota maxima: {max(promedios):.2f}\n"
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
        self.sidebar = CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar_scroll = CTkScrollableFrame(self.sidebar, width=280, height=800)
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
        
        # SCROLLABLE FRAME PRINCIPAL para todo el contenido
        scroll_principal = CTkScrollableFrame(self.tab_clases)
        scroll_principal.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scroll_principal.grid_columnconfigure(0, weight=1)
        
        # ========== CONTENIDO DE LA CLASE (dentro del scroll) ==========
        self.clases_content_frame = CTkFrame(scroll_principal)
        self.clases_content_frame.pack(fill="x", padx=5, pady=5)
        self.clases_content_frame.grid_columnconfigure(0, weight=1)
        
        # --- Encabezado de la clase ---
        CTkLabel(self.clases_content_frame, text="Encabezado de la Clase", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5), padx=10, anchor="w")
        
        self.entry_encabezado_clase = CTkEntry(self.clases_content_frame, 
                                               placeholder_text="Ej: Clase 1 - Introduccion al curso - Fecha: DD/MM/AAAA",
                                               height=35, font=ctk.CTkFont(size=14))
        self.entry_encabezado_clase.pack(fill="x", padx=10, pady=5)
        
        # --- Tópicos a tratar ---
        CTkLabel(self.clases_content_frame, text="Topicos que se trataran:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        
        self.entry_topicos = CTkEntry(self.clases_content_frame, 
                                     placeholder_text="Ej: 1. Presentacion del silabo, 2. Conceptos basicos, 3. Dinamica grupal...",
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
        
        self.texto_clase = ctk.CTkTextbox(self.clases_content_frame, wrap="word", 
                                         font=ctk.CTkFont(size=12), height=250)
        self.texto_clase.pack(fill="x", padx=10, pady=5)
        
        # --- Observaciones/Recordatorios ---
        CTkLabel(self.clases_content_frame, text="Observaciones / Recordatorios:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        
        self.entry_observaciones = CTkEntry(self.clases_content_frame, 
                                           placeholder_text="Ej: Traer material para proxima clase, recordar tarea, etc.",
                                           height=50)
        self.entry_observaciones.pack(fill="x", padx=10, pady=5)
        
        # --- Botones de guardar y exportar (AHORA DENTRO DEL SCROLL) ---
        btn_frame = CTkFrame(self.clases_content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=15)
        
        CTkButton(btn_frame, text="Guardar Clase", command=self.guardar_clase,
                 fg_color="green", height=40).pack(side="left", padx=5, fill="x", expand=True)
        CTkButton(btn_frame, text="Exportar esta clase a PDF", command=self.exportar_clase_pdf,
                 fg_color="blue", height=40).pack(side="left", padx=5, fill="x", expand=True)
        CTkButton(btn_frame, text="Exportar TODAS las clases", command=self.exportar_todas_clases_pdf,
                 fg_color="purple", height=40).pack(side="left", padx=5, fill="x", expand=True)
        
        # ========== PANEL DERECHO: Herramientas (SIN SCROLL, fijo) ==========
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
        
        # --- Botón de Agrupamiento Aleatorio ---
        CTkLabel(self.clases_tools_frame, text="Generador de Grupos", 
                font=ctk.CTkFont(weight="bold")).pack(pady=5, padx=10)
        
        CTkButton(self.clases_tools_frame, text="Crear Grupos Aleatorios", 
                 command=self.abrir_generador_grupos, height=50, fg_color="teal",
                 font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, padx=10, fill="x")
        
        CTkFrame(self.clases_tools_frame, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)
        
        # --- Estado ---
        self.status_clases_label = CTkLabel(self.clases_tools_frame, 
                                             text="Estado: Listo", 
                                             font=ctk.CTkFont(size=12))
        self.status_clases_label.pack(pady=20)
        
        # Cargar clases existentes al iniciar
        self.cargar_lista_clases()
        
        # Bindings para guardado automático
        self.entry_encabezado_clase.bind("<FocusOut>", lambda e: self.guardar_clase_auto())
        self.entry_topicos.bind("<FocusOut>", lambda e: self.guardar_clase_auto())
        self.entry_observaciones.bind("<FocusOut>", lambda e: self.guardar_clase_auto())
        self.texto_clase.bind("<FocusOut>", lambda e: self.guardar_clase_auto())

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
        try:
            seleccion = self.texto_clase.tag_ranges("sel")
            if seleccion:
                inicio = seleccion[0]
                fin = seleccion[1]
                self.texto_clase.tag_add(tipo, inicio, fin)
                if tipo == "bold":
                    self.texto_clase.tag_config(tipo, font=ctk.CTkFont(weight="bold"))
                elif tipo == "italic":
                    self.texto_clase.tag_config(tipo, font=ctk.CTkFont(slant="italic"))
                elif tipo == "underline":
                    self.texto_clase.tag_config(tipo, underline=True)
        except:
            pass

    def guardar_clase_auto(self):
        if hasattr(self, 'clase_actual_id') and self.clase_actual_id:
            self.guardar_clase(silencioso=True)

    def guardar_clase(self, silencioso=False):
        """Guarda la clase actual en archivo JSON"""
        if not self.current_curso:
            if not silencioso:
                messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
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
        
        # Crear ID único si es nueva clase
        if not hasattr(self, 'clase_actual_id') or not self.clase_actual_id:
            from datetime import datetime
            self.clase_actual_id = f"clase_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        datos_clase = {
            "id": self.clase_actual_id,
            "encabezado": encabezado,
            "topicos": topicos,
            "links": links,
            "contenido": contenido,
            "observaciones": observaciones,
            "curso_id": self.current_curso,
            "fecha_modificacion": datetime.now().isoformat()
        }
        
        # GUARDAR EN ARCHIVO JSON
        try:
            archivo_clases = os.path.join(DATA_DIR, f"clases_curso_{self.current_curso}.json")
            
            # Cargar clases existentes
            todas_clases = {}
            if os.path.exists(archivo_clases):
                with open(archivo_clases, 'r', encoding='utf-8') as f:
                    todas_clases = json.load(f)
            
            # Guardar o actualizar esta clase
            todas_clases[self.clase_actual_id] = datos_clase
            
            # Escribir archivo
            with open(archivo_clases, 'w', encoding='utf-8') as f:
                json.dump(todas_clases, f, ensure_ascii=False, indent=2)
            
            # Actualizar lista en memoria
            if not hasattr(self, 'clases_temp'):
                self.clases_temp = {}
            self.clases_temp[self.clase_actual_id] = datos_clase
            
            if not silencioso:
                messagebox.showinfo("Exito", f"Clase guardada correctamente:\n{encabezado[:50]}")
                self.status_clases_label.configure(text=f"Guardado: {encabezado[:30]}...")
                self.cargar_lista_clases()
                
        except Exception as e:
            if not silencioso:
                messagebox.showerror("Error", f"No se pudo guardar la clase:\n{str(e)}")

    def cargar_lista_clases(self):
        if not self.current_curso:
            return
        
        # Cargar desde archivo JSON
        archivo_clases = os.path.join(DATA_DIR, f"clases_curso_{self.current_curso}.json")
        clases = []
        
        if os.path.exists(archivo_clases):
            try:
                with open(archivo_clases, 'r', encoding='utf-8') as f:
                    todas_clases = json.load(f)
                    for clase_id, datos in todas_clases.items():
                        clases.append((clase_id, datos.get("encabezado", "Sin titulo")))
                        # Actualizar memoria también
                        if not hasattr(self, 'clases_temp'):
                            self.clases_temp = {}
                        self.clases_temp[clase_id] = datos
            except Exception as e:
                print(f"Error cargando clases: {e}")
        
        # También revisar memoria
        elif hasattr(self, 'clases_temp'):
            clases = [(k, v["encabezado"]) for k, v in self.clases_temp.items() 
                     if v.get("curso_id") == self.current_curso]
        
        valores = ["-- Nueva Clase --"]
        self.clases_dict = {"-- Nueva Clase --": None}
        
        for clase_id, encabezado in clases:
            display = encabezado[:50] + "..." if len(encabezado) > 50 else encabezado
            valores.append(display)
            self.clases_dict[display] = clase_id
        
        if hasattr(self, 'combo_clases_guardadas') and self.combo_clases_guardadas.winfo_exists():
            self.combo_clases_guardadas.configure(values=valores)
            self.combo_clases_guardadas.set("-- Nueva Clase --")

    def cargar_clase_guardada(self, seleccion):
        """Carga una clase guardada en los campos"""
        if seleccion == "-- Nueva Clase --":
            self.limpiar_campos_clase()
            self.clase_actual_id = None
            return
        
        clase_id = self.clases_dict.get(seleccion)
        if not clase_id:
            return
        
        # Buscar en archivo primero, luego en memoria
        clase_data = None
        archivo_clases = os.path.join(DATA_DIR, f"clases_curso_{self.current_curso}.json")
        
        if os.path.exists(archivo_clases):
            try:
                with open(archivo_clases, 'r', encoding='utf-8') as f:
                    todas_clases = json.load(f)
                    clase_data = todas_clases.get(clase_id)
            except:
                pass
        
        # Si no está en archivo, buscar en memoria
        if not clase_data and hasattr(self, 'clases_temp') and clase_id in self.clases_temp:
            clase_data = self.clases_temp[clase_id]
        
        if clase_data:
            self.clase_actual_id = clase_id
            
            # Limpiar y cargar campos de forma segura
            try:
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

    def limpiar_campos_clase(self):
        self.entry_encabezado_clase.delete(0, "end")
        self.entry_topicos.delete(0, "end")
        self.entry_observaciones.delete(0, "end")
        self.texto_clase.delete("1.0", "end")
        for widget in self.frame_links.winfo_children():
            widget.destroy()
        self.links_entries = []
        self.agregar_campo_link()
        self.status_clases_label.configure(text="Nueva clase")

    def eliminar_clase_guardada(self):
        seleccion = self.combo_clases_guardadas.get()
        if seleccion == "-- Nueva Clase --":
            messagebox.showwarning("Advertencia", "Selecciona una clase para eliminar")
            return
        if messagebox.askyesno("Confirmar", f"Eliminar '{seleccion}'?"):
            clase_id = self.clases_dict.get(seleccion)
            if clase_id and hasattr(self.db, 'eliminar_clase'):
                self.db.eliminar_clase(clase_id)
            elif hasattr(self, 'clases_temp') and clase_id in self.clases_temp:
                del self.clases_temp[clase_id]
            self.cargar_lista_clases()
            self.limpiar_campos_clase()
            messagebox.showinfo("Exito", "Clase eliminada")


    def  abrir_asistencia(self):
        """Abre el diálogo de registro de asistencia con calendario"""
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        # Crear ventana de asistencia
        dialog = ctk.CTkToplevel(self)
        dialog.title("Registro de Asistencia")
        dialog.geometry("700x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # Frame principal dividido en dos columnas
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_columnconfigure(1, weight=2)
        dialog.grid_rowconfigure(0, weight=1)
        
        # ========== PANEL IZQUIERDO: Calendario y controles ==========
        left_frame = CTkFrame(dialog)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        CTkLabel(left_frame, text="Seleccionar Fecha:", 
                font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        
        # Calendario visual
        cal_frame = CTkFrame(left_frame)
        cal_frame.pack(pady=5, padx=10)
        
        # Usar tkcalendar Calendar
        import tkinter as tk
        cal = Calendar(cal_frame, selectmode='day', year=date.today().year, 
                      month=date.today().month, day=date.today().day,
                      locale='es_ES', font="Arial 10", 
                      background='blue', foreground='white',
                      selectbackground='red', selectforeground='yellow')
        cal.pack(pady=5)
        
        # Mostrar fecha seleccionada
        fecha_label = CTkLabel(left_frame, text=f"Fecha: {cal.get_date()}", 
                              font=ctk.CTkFont(size=14, weight="bold"))
        fecha_label.pack(pady=10)
        
        def actualizar_fecha_label():
            fecha_label.configure(text=f"Fecha: {cal.get_date()}")
            dialog.after(100, actualizar_fecha_label)
        actualizar_fecha_label()
        
        # Botones de acción
        btn_frame = CTkFrame(left_frame, fg_color="transparent")
        btn_frame.pack(pady=20, fill="x", padx=10)
        
        CTkButton(btn_frame, text="Marcar Todos Presentes", 
                 command=lambda: self.marcar_todos_asistencia("presente"),
                 fg_color="green").pack(pady=2, fill="x")
        CTkButton(btn_frame, text="Marcar Todos Ausentes", 
                 command=lambda: self.marcar_todos_asistencia("ausente"),
                 fg_color="red").pack(pady=2, fill="x")
        CTkButton(btn_frame, text="Guardar Asistencia", 
                 command=lambda: self.guardar_asistencia(cal.get_date(), dialog),
                 fg_color="blue", height=40, font=ctk.CTkFont(weight="bold")).pack(pady=10, fill="x")
        
        # Estadísticas del día
        self.stats_label = CTkLabel(left_frame, text="Estadísticas: -", 
                                   font=ctk.CTkFont(size=12))
        self.stats_label.pack(pady=10)
        
        # ========== PANEL DERECHO: Lista de estudiantes ==========
        right_frame = CTkFrame(dialog)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        
        CTkLabel(right_frame, text="Lista de Estudiantes", 
                font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        # Scrollable frame para estudiantes
        self.asistencia_scroll = CTkScrollableFrame(right_frame, label_text="Marcar asistencia")
        self.asistencia_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Cargar estudiantes y crear checkboxes
        self.checkboxes_asistencia = {}
        self.cargar_estudiantes_asistencia(cal.get_date())
        
        # Actualizar al cambiar fecha en calendario
        def on_fecha_change(event=None):
            self.cargar_estudiantes_asistencia(cal.get_date())
        
        cal.bind("<<CalendarSelected>>", on_fecha_change)

    def cargar_estudiantes_asistencia(self, fecha_str):
        """Carga la lista de estudiantes con sus estados de asistencia para una fecha"""
        # Limpiar frame anterior
        for widget in self.asistencia_scroll.winfo_children():
            widget.destroy()
        self.checkboxes_asistencia = {}
        
        estudiantes = self.db.get_estudiantes(self.current_curso)
        if not estudiantes:
            CTkLabel(self.asistencia_scroll, text="No hay estudiantes en este curso").pack(pady=20)
            return
        
        # Cargar asistencia previa si existe
        asistencia_previa = self.cargar_asistencia_fecha(fecha_str)
        
        presentes = 0
        ausentes = 0
        sin_marcar = 0
        
        for est in estudiantes:
            est_id, nombre, grupo, email = est
            
            # Frame para cada estudiante
            row = CTkFrame(self.asistencia_scroll)
            row.pack(fill="x", pady=2, padx=5)
            
            # Nombre del estudiante
            nombre_text = f"{nombre}" + (f" (G{grupo})" if grupo > 1 else "")
            CTkLabel(row, text=nombre_text, font=ctk.CTkFont(size=12)).pack(side="left", padx=5)
            
            # Frame para los radio buttons
            radio_frame = CTkFrame(row, fg_color="transparent")
            radio_frame.pack(side="right", padx=5)
            
            # Variable para el estado
            estado_var = ctk.StringVar(value=asistencia_previa.get(str(est_id), "sin_marcar"))
            
            # Radio button Presente
            rb_presente = CTkRadioButton(radio_frame, text="Presente", 
                                        variable=estado_var, value="presente",
                                        fg_color="green", hover_color="darkgreen")
            rb_presente.pack(side="left", padx=10)
            
            # Radio button Ausente
            rb_ausente = CTkRadioButton(radio_frame, text="Ausente", 
                                       variable=estado_var, value="ausente",
                                       fg_color="red", hover_color="darkred")
            rb_ausente.pack(side="left", padx=10)
            
            self.checkboxes_asistencia[est_id] = estado_var
            
            # Contar para estadísticas
            if estado_var.get() == "presente":
                presentes += 1
            elif estado_var.get() == "ausente":
                ausentes += 1
            else:
                sin_marcar += 1
        
        # Actualizar estadísticas
        total = len(estudiantes)
        if hasattr(self, 'stats_label'):
            self.stats_label.configure(
                text=f"Presentes: {presentes} | Ausentes: {ausentes} | Sin marcar: {sin_marcar}\nTotal: {total}"
            )

    def marcar_todos_asistencia(self, estado):
        """Marca todos los estudiantes con el mismo estado"""
        for var in self.checkboxes_asistencia.values():
            var.set(estado)
        # Recargar para actualizar estadísticas
        # (simplificado - en producción optimizar)

    def guardar_asistencia(self, fecha_str, dialog):
        """Guarda el registro de asistencia"""
        asistencia_data = {
            "fecha": fecha_str,
            "curso_id": self.current_curso,
            "estudiantes": {}
        }
        
        for est_id, var in self.checkboxes_asistencia.items():
            estado = var.get()
            if estado != "sin_marcar":
                asistencia_data["estudiantes"][str(est_id)] = estado
        
        # Guardar en archivo JSON (temporal hasta tener DB)
        archivo_asistencia = os.path.join(DATA_DIR, f"asistencia_{self.current_curso}.json")
        
        # Cargar datos existentes
        todas_asistencias = {}
        if os.path.exists(archivo_asistencia):
            with open(archivo_asistencia, 'r', encoding='utf-8') as f:
                todas_asistencias = json.load(f)
        
        # Actualizar con nueva asistencia
        todas_asistencias[fecha_str] = asistencia_data
        
        # Guardar
        with open(archivo_asistencia, 'w', encoding='utf-8') as f:
            json.dump(todas_asistencias, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo("Éxito", f"Asistencia guardada para el {fecha_str}")
        dialog.destroy()

    def cargar_asistencia_fecha(self, fecha_str):
        """Carga la asistencia de una fecha específica"""
        archivo_asistencia = os.path.join(DATA_DIR, f"asistencia_{self.current_curso}.json")
        
        if os.path.exists(archivo_asistencia):
            with open(archivo_asistencia, 'r', encoding='utf-8') as f:
                todas_asistencias = json.load(f)
                if fecha_str in todas_asistencias:
                    return todas_asistencias[fecha_str].get("estudiantes", {})
        return {}

    def abrir_generador_grupos(self):
        """Abre el generador de grupos aleatorios con funcionalidad de arrastrar"""
        if not self.current_curso:
            messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        
        from random import shuffle
        import json
        
        # Crear ventana
        dialog = ctk.CTkToplevel(self)
        dialog.title("Generador de Grupos")
        dialog.geometry("900x700")
        dialog.transient(self)
        dialog.grab_set()
        
        # Frame principal
        main_frame = CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ========== PANEL SUPERIOR: Controles ==========
        control_frame = CTkFrame(main_frame)
        control_frame.pack(fill="x", pady=5, padx=5)
        
        CTkLabel(control_frame, text="Cantidad de grupos:", 
                font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        
        self.num_grupos_var = ctk.StringVar(value="3")
        entry_num = CTkEntry(control_frame, textvariable=self.num_grupos_var, width=50)
        entry_num.pack(side="left", padx=5)
        
        # Opción: usar solo presentes o todos
        self.usar_presentes_var = ctk.BooleanVar(value=False)
        check_presentes = CTkCheckBox(control_frame, text="Solo estudiantes presentes hoy", 
                                     variable=self.usar_presentes_var)
        check_presentes.pack(side="left", padx=20)
        
        CTkButton(control_frame, text="Generar Grupos Aleatorios", 
                 command=lambda: self.generar_grupos_aleatorios(),
                 fg_color="green", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        
        CTkButton(control_frame, text="Guardar Grupos", 
                 command=lambda: self.guardar_grupos(dialog),
                 fg_color="blue").pack(side="right", padx=10)
        
        # ========== PANEL CENTRAL: Grupos ==========
        self.grupos_frame = CTkScrollableFrame(main_frame, label_text="Grupos generados")
        self.grupos_frame.pack(fill="both", expand=True, pady=10, padx=5)
        
        # Diccionario para almacenar los frames y labels de cada grupo
        self.grupos_containers = {}
        self.estudiantes_grupos = {}
        
        # Cargar grupos previos si existen
        self.cargar_grupos_previos()

    def generar_grupos_aleatorios(self):
        """Genera grupos aleatorios de estudiantes"""
        from random import shuffle
        
        try:
            num_grupos = int(self.num_grupos_var.get())
            if num_grupos < 2:
                messagebox.showwarning("Advertencia", "Debe haber al menos 2 grupos")
                return
        except ValueError:
            messagebox.showerror("Error", "Ingresa un numero valido de grupos")
            return
        
        # Obtener estudiantes
        if self.usar_presentes_var.get():
            # Solo presentes del dia de hoy
            from datetime import date
            fecha_hoy = date.today().strftime("%d/%m/%Y")
            asistencia = self.cargar_asistencia_fecha(fecha_hoy)
            presentes_ids = [int(k) for k, v in asistencia.items() if v == "presente"]
            estudiantes = [e for e in self.db.get_estudiantes(self.current_curso) 
                          if e[0] in presentes_ids]
            if not estudiantes:
                messagebox.showwarning("Advertencia", "No hay estudiantes presentes hoy")
                return
        else:
            # Todos los estudiantes
            estudiantes = self.db.get_estudiantes(self.current_curso)
            if not estudiantes:
                messagebox.showwarning("Advertencia", "No hay estudiantes en este curso")
                return
        
        # Mezclar aleatoriamente
        lista_estudiantes = list(estudiantes)
        shuffle(lista_estudiantes)
        
        # Distribuir en grupos
        self.estudiantes_grupos = {i: [] for i in range(num_grupos)}
        for i, est in enumerate(lista_estudiantes):
            grupo_num = i % num_grupos
            self.estudiantes_grupos[grupo_num].append(est)
        
        # Mostrar grupos
        self.mostrar_grupos_en_pantalla()

    def mostrar_grupos_en_pantalla(self):
        """Muestra los grupos generados en la interfaz con funcionalidad de arrastrar"""
        # Limpiar frame anterior
        for widget in self.grupos_frame.winfo_children():
            widget.destroy()
        self.grupos_containers = {}
        
        if not self.estudiantes_grupos:
            CTkLabel(self.grupos_frame, text="Genera grupos primero").pack(pady=20)
            return
        
        # Crear grid de grupos (max 3 columnas)
        num_grupos = len(self.estudiantes_grupos)
        cols = 3 if num_grupos >= 3 else num_grupos
        
        for idx in range(num_grupos):
            row = idx // cols
            col = idx % cols
            
            # Frame del grupo
            grupo_frame = CTkFrame(self.grupos_frame, border_width=2, border_color="blue")
            grupo_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # Configurar peso para expansión
            self.grupos_frame.grid_columnconfigure(col, weight=1)
            
            # Header del grupo
            CTkLabel(grupo_frame, text=f"GRUPO {idx + 1}", 
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="blue").pack(pady=(10, 5))
            
            CTkLabel(grupo_frame, text=f"({len(self.estudiantes_grupos[idx])} estudiantes)", 
                    font=ctk.CTkFont(size=10)).pack()
            
            # Separador
            CTkFrame(grupo_frame, height=2, fg_color="gray").pack(fill="x", padx=5, pady=5)
            
            # Frame scrollable para estudiantes de este grupo
            est_frame = CTkScrollableFrame(grupo_frame, height=200, width=250)
            est_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            self.grupos_containers[idx] = est_frame
            
            # Mostrar estudiantes con botones para mover
            for est in self.estudiantes_grupos[idx]:
                est_id, nombre, grupo_num, email = est
                
                est_row = CTkFrame(est_frame, fg_color="transparent")
                est_row.pack(fill="x", pady=1)
                
                CTkLabel(est_row, text=f"• {nombre}", 
                        font=ctk.CTkFont(size=11)).pack(side="left", padx=2)
                
                # Botones para mover entre grupos
                btn_frame = CTkFrame(est_row, fg_color="transparent")
                btn_frame.pack(side="right")
                
                if idx > 0:  # Puede mover a grupo anterior
                    CTkButton(btn_frame, text="←", width=25, 
                             command=lambda e=est, g=idx: self.mover_estudiante_grupo(e, g, g-1),
                             fg_color="gray", hover_color="darkgray").pack(side="left", padx=1)
                
                if idx < num_grupos - 1:  # Puede mover a grupo siguiente
                    CTkButton(btn_frame, text="→", width=25,
                             command=lambda e=est, g=idx: self.mover_estudiante_grupo(e, g, g+1),
                             fg_color="gray", hover_color="darkgray").pack(side="left", padx=1)
                
                # Botón para eliminar del grupo (mover a lista de sin grupo)
                CTkButton(btn_frame, text="×", width=25,
                         command=lambda e=est, g=idx: self.quitar_de_grupo(e, g),
                         fg_color="red", hover_color="darkred").pack(side="left", padx=1)

    def mover_estudiante_grupo(self, estudiante, grupo_origen, grupo_destino):
        """Mueve un estudiante de un grupo a otro"""
        if estudiante in self.estudiantes_grupos[grupo_origen]:
            self.estudiantes_grupos[grupo_origen].remove(estudiante)
            self.estudiantes_grupos[grupo_destino].append(estudiante)
            self.mostrar_grupos_en_pantalla()

    def quitar_de_grupo(self, estudiante, grupo):
        """Quita un estudiante de un grupo (lo deja sin asignar)"""
        if estudiante in self.estudiantes_grupos[grupo]:
            self.estudiantes_grupos[grupo].remove(estudiante)
            # Crear grupo especial "-1" para no asignados si no existe
            if -1 not in self.estudiantes_grupos:
                self.estudiantes_grupos[-1] = []
            self.estudiantes_grupos[-1].append(estudiante)
            self.mostrar_grupos_en_pantalla()

    def guardar_grupos(self, dialog):
        """Guarda la configuración de grupos"""
        import json
        from datetime import datetime
        
        if not self.estudiantes_grupos:
            messagebox.showwarning("Advertencia", "No hay grupos para guardar")
            return
        
        # Convertir a formato guardable (solo IDs)
        grupos_guardar = {}
        for num, estudiantes in self.estudiantes_grupos.items():
            if num >= 0:  # Ignorar el grupo -1 (no asignados) al guardar
                grupos_guardar[f"grupo_{num + 1}"] = [e[0] for e in estudiantes]
        
        datos = {
            "fecha_creacion": datetime.now().isoformat(),
            "curso_id": self.current_curso,
            "num_grupos": len([k for k in self.estudiantes_grupos.keys() if k >= 0]),
            "grupos": grupos_guardar
        }
        
        # Guardar en JSON
        archivo = os.path.join(DATA_DIR, f"grupos_{self.current_curso}.json")
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo("Exito", f"Grupos guardados correctamente\nArchivo: {archivo}")
        dialog.destroy()

    def cargar_grupos_previos(self):
        """Carga grupos previos si existen"""
        import json
        
        archivo = os.path.join(DATA_DIR, f"grupos_{self.current_curso}.json")
        if os.path.exists(archivo):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                
                # Reconstruir grupos desde IDs
                todos_estudiantes = {e[0]: e for e in self.db.get_estudiantes(self.current_curso)}
                
                self.estudiantes_grupos = {}
                for nombre_grupo, ids in datos.get("grupos", {}).items():
                    num = int(nombre_grupo.split("_")[1]) - 1
                    self.estudiantes_grupos[num] = [todos_estudiantes[eid] for eid in ids if eid in todos_estudiantes]
                
                self.num_grupos_var.set(str(len(self.estudiantes_grupos)))
                self.mostrar_grupos_en_pantalla()
                
            except Exception as e:
                print(f"Error cargando grupos previos: {e}")


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
            contenido = self.texto_clase.get("1.0", "end").strip() if hasattr(self, 'texto_clase') and self.texto_clase.winfo_exists() else ""
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
        
        # Obtener todas las clases
        clases = []
        if hasattr(self.db, 'get_clases'):
            try:
                clases = self.db.get_clases(self.current_curso)
            except:
                clases = []
        elif hasattr(self, 'clases_temp'):
            clases = [(k, v["encabezado"]) for k, v in self.clases_temp.items() 
                     if v.get("curso_id") == self.current_curso]
        
        if not clases:
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
            elementos.append(Paragraph(f"<b>Total de clases:</b> {len(clases)}", estilo_normal))
            elementos.append(Paragraph(f"<b>Fecha de exportacion:</b> {datetime.now().strftime('%d/%m/%Y')}", estilo_normal))
            elementos.append(PageBreak())
            
            # Cada clase
            for idx, (clase_id, encabezado) in enumerate(clases, 1):
                # Obtener datos de la clase
                clase_data = None
                if hasattr(self.db, 'get_clase_por_id'):
                    try:
                        clase_data = self.db.get_clase_por_id(clase_id)
                    except:
                        clase_data = None
                elif hasattr(self, 'clases_temp') and clase_id in self.clases_temp:
                    clase_data = self.clases_temp[clase_id]
                
                if not clase_data:
                    continue
                
                # Numero de clase
                elementos.append(Paragraph(f"CLASE {idx}", estilo_titulo))
                elementos.append(Paragraph(f"<b>{clase_data.get('encabezado', 'Sin titulo')}</b>", estilo_subtitulo))
                
                # Topicos
                topicos = clase_data.get('topicos', '')
                if topicos:
                    elementos.append(Paragraph("<b>Topicos:</b> " + topicos, estilo_normal))
                
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
            messagebox.showinfo("Exito", f"PDF con {len(clases)} clases guardado:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el PDF:\n{str(e)}")

if __name__ == "__main__":
    app = GestorNotasApp()
    app.mainloop()