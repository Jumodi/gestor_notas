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
        self.tab_config = self.tabview.add("Configuracion del Curso")
        self.tab_resumen = self.tabview.add("Resumen y Estadisticas")
        self.tab_clases = self.tabview.add("Control de Clases")
        self.setup_tab_notas()
        self.setup_tab_config()
        self.setup_tab_resumen()
        self.setup_tab_clases()

    def setup_tab_clases(self):
        self.tab_clases.grid_columnconfigure(0, weight=3)
        self.tab_clases.grid_columnconfigure(1, weight=1)
        self.tab_clases.grid_rowconfigure(0, weight=1)
        self.clases_content_frame = CTkFrame(self.tab_clases)
        self.clases_content_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.clases_content_frame.grid_columnconfigure(0, weight=1)
        CTkLabel(self.clases_content_frame, text="Encabezado de la Clase", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5), padx=10, anchor="w")
        self.entry_encabezado_clase = CTkEntry(self.clases_content_frame, placeholder_text="Ej: Clase 1 - Introduccion al curso - Fecha: DD/MM/AAAA", height=35, font=ctk.CTkFont(size=14))
        self.entry_encabezado_clase.pack(fill="x", padx=10, pady=5)
        CTkLabel(self.clases_content_frame, text="Topicos que se trataran:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        self.entry_topicos = CTkEntry(self.clases_content_frame, placeholder_text="Ej: 1. Presentacion del silabo, 2. Conceptos basicos, 3. Dinamica grupal...", height=35)
        self.entry_topicos.pack(fill="x", padx=10, pady=5)
        CTkLabel(self.clases_content_frame, text="Enlaces de Lecturas Asignadas:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        self.frame_links = CTkFrame(self.clases_content_frame)
        self.frame_links.pack(fill="x", padx=10, pady=5)
        self.links_entries = []
        CTkButton(self.clases_content_frame, text="Agregar Enlace", command=self.agregar_campo_link, fg_color="blue").pack(pady=5, padx=10, anchor="w")
        self.agregar_campo_link()
        CTkLabel(self.clases_content_frame, text="Desarrollo de la Clase (Notas):", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        toolbar_frame = CTkFrame(self.clases_content_frame, fg_color="transparent")
        toolbar_frame.pack(fill="x", padx=10, pady=2)
        CTkButton(toolbar_frame, text="Negrita", width=80, command=lambda: self.aplicar_formato_texto("bold")).pack(side="left", padx=2)
        CTkButton(toolbar_frame, text="Cursiva", width=80, command=lambda: self.aplicar_formato_texto("italic")).pack(side="left", padx=2)
        CTkButton(toolbar_frame, text="Subrayado", width=80, command=lambda: self.aplicar_formato_texto("underline")).pack(side="left", padx=2)
        self.texto_clase = ctk.CTkTextbox(self.clases_content_frame, wrap="word", font=ctk.CTkFont(size=12), height=250)
        self.texto_clase.pack(fill="both", expand=True, padx=10, pady=5)
        CTkLabel(self.clases_content_frame, text="Observaciones / Recordatorios:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=10, anchor="w")
        self.entry_observaciones = CTkEntry(self.clases_content_frame, placeholder_text="Ej: Traer material para proxima clase, recordar tarea, etc.", height=50)
        self.entry_observaciones.pack(fill="x", padx=10, pady=5)
        btn_frame = CTkFrame(self.clases_content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=15)
        CTkButton(btn_frame, text="Guardar Clase", command=self.guardar_clase, fg_color="green", height=40).pack(side="left", padx=5, fill="x", expand=True)
        CTkButton(btn_frame, text="Exportar esta clase a PDF", command=self.exportar_clase_pdf, fg_color="blue", height=40).pack(side="left", padx=5, fill="x", expand=True)
        CTkButton(btn_frame, text="Exportar TODAS las clases", command=self.exportar_todas_clases_pdf, fg_color="purple", height=40).pack(side="left", padx=5, fill="x", expand=True)
        self.clases_tools_frame = CTkFrame(self.tab_clases)
        self.clases_tools_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        CTkLabel(self.clases_tools_frame, text="Clases Guardadas", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5), padx=10)
        self.combo_clases_guardadas = CTkOptionMenu(self.clases_tools_frame, values=["-- Nueva Clase --"], command=self.cargar_clase_guardada)
        self.combo_clases_guardadas.pack(fill="x", padx=10, pady=5)
        CTkButton(self.clases_tools_frame, text="Eliminar Clase Seleccionada", command=self.eliminar_clase_guardada, fg_color="red").pack(pady=5, padx=10, fill="x")
        CTkFrame(self.clases_tools_frame, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)
        CTkLabel(self.clases_tools_frame, text="Control de Asistencia", font=ctk.CTkFont(weight="bold")).pack(pady=5, padx=10)
        CTkButton(self.clases_tools_frame, text="Registrar Asistencia", command=self.abrir_asistencia, height=50, fg_color="orange", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, padx=10, fill="x")
        CTkFrame(self.clases_tools_frame, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)
        CTkLabel(self.clases_tools_frame, text="Generador de Grupos", font=ctk.CTkFont(weight="bold")).pack(pady=5, padx=10)
        CTkButton(self.clases_tools_frame, text="Crear Grupos Aleatorios", command=self.abrir_generador_grupos, height=50, fg_color="teal", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10, padx=10, fill="x")
        CTkFrame(self.clases_tools_frame, height=2, fg_color="gray").pack(fill="x", padx=10, pady=15)
        self.status_clases_label = CTkLabel(self.clases_tools_frame, text="Estado: Listo", font=ctk.CTkFont(size=12))
        self.status_clases_label.pack(pady=20)
        self.cargar_lista_clases()
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
        if not self.current_curso:
            if not silencioso:
                messagebox.showwarning("Advertencia", "Selecciona un curso primero")
            return
        encabezado = self.entry_encabezado_clase.get().strip()
        topicos = self.entry_topicos.get().strip()
        observaciones = self.entry_observaciones.get().strip()
        contenido = self.texto_clase.get("1.0", "end").strip()
        links = []
        for nombre_entry, url_entry in self.links_entries:
            nombre = nombre_entry.get().strip()
            url = url_entry.get().strip()
            if nombre or url:
                links.append({"nombre": nombre, "url": url})
        if not encabezado:
            from datetime import datetime
            encabezado = f"Clase del {datetime.now().strftime('%d/%m/%Y')}"
            self.entry_encabezado_clase.insert(0, encabezado)
        datos_clase = {
            "encabezado": encabezado,
            "topicos": topicos,
            "links": links,
            "contenido": contenido,
            "observaciones": observaciones,
            "curso_id": self.current_curso,
            "fecha_modificacion": datetime.now().isoformat()
        }
        if hasattr(self.db, 'guardar_clase'):
            clase_id = self.db.guardar_clase(datos_clase, getattr(self, 'clase_actual_id', None))
            self.clase_actual_id = clase_id
            if not silencioso:
                messagebox.showinfo("Exito", "Clase guardada correctamente")
                self.status_clases_label.configure(text=f"Guardado: {encabezado[:30]}...")
                self.cargar_lista_clases()
        else:
            if not hasattr(self, 'clases_temp'):
                self.clases_temp = {}
            self.clase_actual_id = self.clase_actual_id or f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.clases_temp[self.clase_actual_id] = datos_clase
            if not silencioso:
                messagebox.showinfo("Exito", "Clase guardada (modo temporal)")

    def cargar_lista_clases(self):
        if not self.current_curso:
            return
        clases = []
        if hasattr(self.db, 'get_clases'):
            clases = self.db.get_clases(self.current_curso)
        elif hasattr(self, 'clases_temp'):
            clases = [(k, v["encabezado"]) for k, v in self.clases_temp.items() if v.get("curso_id") == self.current_curso]
        valores = ["-- Nueva Clase --"]
        self.clases_dict = {"-- Nueva Clase --": None}
        for clase_id, encabezado in clases:
            display = encabezado[:50] + "..." if len(encabezado) > 50 else encabezado
            valores.append(display)
            self.clases_dict[display] = clase_id
        self.combo_clases_guardadas.configure(values=valores)
        self.combo_clases_guardadas.set("-- Nueva Clase --")

    def cargar_clase_guardada(self, seleccion):
        if seleccion == "-- Nueva Clase --":
            self.limpiar_campos_clase()
            self.clase_actual_id = None
            return
        clase_id = self.clases_dict.get(seleccion)
        if not clase_id:
            return
        clase_data = None
        if hasattr(self.db, 'get_clase_por_id'):
            clase_data = self.db.get_clase_por_id(clase_id)
        elif hasattr(self, 'clases_temp') and clase_id in self.clases_temp:
            clase_data = self.clases_temp[clase_id]
        if clase_data:
            self.clase_actual_id = clase_id
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

    def exportar_clase_pdf(self):
        messagebox.showinfo("En desarrollo", "La exportacion a PDF se implementara en el siguiente paso. Por ahora puedes copiar el contenido manualmente.")

    def exportar_todas_clases_pdf(self):
        messagebox.showinfo("En desarrollo", "La exportacion multiple a PDF se implementara en el siguiente paso.")

    def abrir_asistencia(self):
        messagebox.showinfo("En desarrollo", "La funcionalidad de asistencia se implementara en el siguiente paso.")

    def abrir_generador_grupos(self):
        messagebox.showinfo("En desarrollo", "La funcionalidad de generador de grupos se implementara en el siguiente paso.")


if __name__ == "__main__":
    app = GestorNotasApp()
    app.mainloop()