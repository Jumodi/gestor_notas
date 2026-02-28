import os
import json
import hashlib
import base64
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import shutil
import time
import platform

class FileSyncManager:
    """
    Sistema de sincronizacion por archivo compartido encriptado.
    Compatible con Dropbox, iCloud, OneDrive, NAS, USB, etc.
    """
    
    def __init__(self, db_path, sync_folder=None, password=None):
        self.db_path = db_path
        self.system = platform.system()
        
        self.config_file = os.path.join(os.path.dirname(db_path), "sync_config.json")
        
        self.config = self._load_config()
        
        if sync_folder:
            self.sync_folder = sync_folder
            self.config["sync_folder"] = sync_folder
            self._save_config()
        else:
            self.sync_folder = self.config.get("sync_folder")
        
        self.password = password or self.config.get("password", "default_password_change_me")
        
        self.sync_file = os.path.join(self.sync_folder, "notas_sync.enc") if self.sync_folder else None
        self.meta_file = os.path.join(self.sync_folder, "notas_sync.meta") if self.sync_folder else None
        
        self.last_hash = None
        
    def _load_config(self):
        """Carga configuracion de sincronizacion"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_config(self):
        """Guarda configuracion de sincronizacion"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error guardando config: {e}")
    
    def _derive_key(self, password, salt=None):
        """Deriva una clave AES-256 desde la contrasena"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def _calculate_hash(self, filepath):
        """Calcula hash SHA-256 del archivo"""
        if not os.path.exists(filepath):
            return None
        
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_file_timestamp(self, filepath):
        """Obtiene timestamp de modificacion del archivo"""
        if not os.path.exists(filepath):
            return 0
        return os.path.getmtime(filepath)
    
    def setup_sync_folder(self, folder_path):
        """
        Configura la carpeta de sincronizacion.
        Detecta automaticamente servicios comunes.
        """
        folder_path = os.path.expanduser(folder_path)
        
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                return False, f"No se pudo crear la carpeta: {str(e)}"
        
        test_file = os.path.join(folder_path, ".write_test")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            return False, f"No hay permisos de escritura en la carpeta: {str(e)}"
        
        self.sync_folder = folder_path
        self.sync_file = os.path.join(folder_path, "notas_sync.enc")
        self.meta_file = os.path.join(folder_path, "notas_sync.meta")
        
        self.config["sync_folder"] = folder_path
        self._save_config()
        
        servicio = self._detectar_servicio(folder_path)
        
        return True, f"Carpeta configurada: {folder_path}\nServicio detectado: {servicio}"
    
    def _detectar_servicio(self, path):
        """Detecta el servicio de almacenamiento basado en la ruta"""
        path_lower = path.lower()
        
        if "dropbox" in path_lower:
            return "Dropbox"
        elif "icloud" in path_lower or "cloud" in path_lower:
            return "iCloud"
        elif "onedrive" in path_lower:
            return "OneDrive"
        elif "google drive" in path_lower or "googledrive" in path_lower:
            return "Google Drive (carpeta local)"
        elif "box" in path_lower:
            return "Box"
        elif "synology" in path_lower or "nas" in path_lower:
            return "NAS"
        elif "usb" in path_lower or "volumes" in path_lower or "media" in path_lower:
            return "Unidad externa/USB"
        else:
            return "Carpeta local/Red"
    
    def export_to_sync(self, comentario=""):
        """
        Exporta la base de datos a archivo encriptado en la carpeta compartida.
        """
        if not self.sync_folder:
            return False, "No hay carpeta de sincronizacion configurada"
        
        if not os.path.exists(self.db_path):
            return False, "No se encontro la base de datos local"
        
        try:
            with open(self.db_path, 'rb') as f:
                db_data = f.read()
            
            salt = os.urandom(16)
            key, _ = self._derive_key(self.password, salt)
            fernet = Fernet(key)
            
            encrypted_data = fernet.encrypt(db_data)
            
            with open(self.sync_file, 'wb') as f:
                f.write(salt + encrypted_data)
            
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "hash_local": self._calculate_hash(self.db_path),
                "size_original": len(db_data),
                "size_encrypted": len(encrypted_data),
                "comentario": comentario,
                "dispositivo": platform.node(),
                "sistema": self.system
            }
            
            with open(self.meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.last_hash = metadata["hash_local"]
            
            return True, f"Exportado correctamente\n{metadata['timestamp']}\nDispositivo: {metadata['dispositivo']}"
            
        except Exception as e:
            return False, f"Error al exportar: {str(e)}"
    
    def import_from_sync(self, forzar=False):
        """
        Importa la base de datos desde el archivo encriptado.
        Verifica cambios por hash.
        """
        if not self.sync_folder:
            return False, "No hay carpeta de sincronizacion configurada", None
        
        if not os.path.exists(self.sync_file):
            return False, "No hay archivo de sincronizacion en la carpeta", None
        
        try:
            metadata = {}
            if os.path.exists(self.meta_file):
                with open(self.meta_file, 'r') as f:
                    metadata = json.load(f)
            
            hash_local_actual = self._calculate_hash(self.db_path)
            
            hash_sync = metadata.get("hash_local", "desconocido")
            
            if hash_local_actual == hash_sync and not forzar and os.path.exists(self.db_path):
                return True, "Los archivos estan sincronizados (mismo hash)", "sincronizado"
            
            with open(self.sync_file, 'rb') as f:
                data = f.read()
            
            salt = data[:16]
            encrypted_data = data[16:]
            
            key, _ = self._derive_key(self.password, salt)
            fernet = Fernet(key)
            
            try:
                db_data = fernet.decrypt(encrypted_data)
            except Exception:
                return False, "Error de desencriptacion. Verifica la contrasena.", None
            
            if os.path.exists(self.db_path):
                backup_path = self.db_path + ".backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.copy2(self.db_path, backup_path)
            
            with open(self.db_path, 'wb') as f:
                f.write(db_data)
            
            self.last_hash = self._calculate_hash(self.db_path)
            
            info_import = {
                "fecha_export": metadata.get("timestamp", "desconocida"),
                "dispositivo_origen": metadata.get("dispositivo", "desconocido"),
                "comentario": metadata.get("comentario", ""),
                "tamaño": len(db_data)
            }
            
            return True, "Importado correctamente", info_import
            
        except Exception as e:
            return False, f"Error al importar: {str(e)}", None
    
    def check_sync_status(self):
        """
        Verifica el estado de sincronizacion.
        Retorna: estado, mensaje, info
        """
        if not self.sync_folder:
            return "no_config", "Sin carpeta de sincronizacion configurada", None
        
        if not os.path.exists(self.sync_file):
            return "no_sync_file", "No hay archivo de sincronizacion", None
        
        metadata = {}
        if os.path.exists(self.meta_file):
            try:
                with open(self.meta_file, 'r') as f:
                    metadata = json.load(f)
            except:
                pass
        
        hash_local = self._calculate_hash(self.db_path)
        hash_sync = metadata.get("hash_local", None)
        timestamp_sync = metadata.get("timestamp", "desconocido")
        
        tiempo_local = self._get_file_timestamp(self.db_path) if os.path.exists(self.db_path) else 0
        tiempo_sync_file = self._get_file_timestamp(self.sync_file)
        
        info = {
            "hash_local": hash_local,
            "hash_sync": hash_sync,
            "timestamp_sync": timestamp_sync,
            "tiempo_local": tiempo_local,
            "tiempo_sync_file": tiempo_sync_file,
            "dispositivo_origen": metadata.get("dispositivo", "desconocido"),
            "comentario": metadata.get("comentario", "")
        }
        
        if not hash_sync:
            return "sin_metadata", "Archivo de sync sin metadata", info
        
        if hash_local == hash_sync:
            return "sincronizado", "Sincronizado correctamente", info
        
        if tiempo_local > tiempo_sync_file and hash_local != hash_sync:
            return "conflicto", "Conflicto: ambas versiones tienen cambios", info
        
        if tiempo_sync_file > tiempo_local:
            return "necesita_importar", "Hay cambios en la nube para importar", info
        
        return "desconocido", "Estado desconocido", info
    
    def resolver_conflicto(self, usar_local=True, comentario=""):
        """
        Resuelve un conflicto de sincronizacion.
        usar_local=True: sube version local
        usar_local=False: importa version de la nube
        """
        if usar_local:
            return self.export_to_sync(f"Resuelto conflicto - version local. {comentario}")
        else:
            return self.import_from_sync(forzar=True)
    
    def get_default_sync_paths(self):
        """
        Retorna rutas predeterminadas de servicios comunes segun el sistema.
        """
        paths = []
        home = os.path.expanduser("~")
        
        if self.system == "Windows":
            paths.append(("Dropbox", os.path.join(home, "Dropbox")))
            paths.append(("OneDrive", os.path.join(home, "OneDrive")))
            paths.append(("iCloud", os.path.join(home, "iCloudDrive")))
            
        elif self.system == "Darwin":
            paths.append(("Dropbox", os.path.join(home, "Dropbox")))
            paths.append(("iCloud Drive", os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs")))
            paths.append(("OneDrive", os.path.join(home, "OneDrive")))
            
        else:
            paths.append(("Dropbox", os.path.join(home, "Dropbox")))
        
        return [(nombre, ruta) for nombre, ruta in paths if os.path.exists(ruta)]
    
    def verify_password(self, password_test):
        """
        Verifica si una contrasena puede desencriptar el archivo de sync.
        """
        if not os.path.exists(self.sync_file):
            return True
        
        try:
            with open(self.sync_file, 'rb') as f:
                data = f.read()
            
            salt = data[:16]
            encrypted_data = data[16:]
            
            key, _ = self._derive_key(password_test, salt)
            fernet = Fernet(key)
            fernet.decrypt(encrypted_data)
            
            return True
        except:
            return False