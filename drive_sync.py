import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

class GoogleDriveSync:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.folder_id = None
    
    def authenticate(self):
        """Autentica con Google Drive"""
        creds = None
        
        # Cargar token existente
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        # Si no hay credenciales válidas, hacer login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    return False, f"No se encontró {self.credentials_path}. Descárgalo desde Google Cloud Console."
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Guardar token para futuras ejecuciones
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        return True, "Autenticación exitosa"
    
    def crear_carpeta(self, nombre, parent_id=None):
        """Crea una carpeta en Google Drive"""
        if not self.service:
            return None
        
        file_metadata = {
            'name': nombre,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id] if parent_id else []
        }
        
        try:
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            return file.get('id')
        except Exception as e:
            print(f"Error creando carpeta: {e}")
            return None
    
    def buscar_carpeta(self, nombre):
        """Busca una carpeta por nombre"""
        if not self.service:
            return None
        
        query = f"mimeType='application/vnd.google-apps.folder' and name='{nombre}' and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        return items[0]['id'] if items else None
    
    def subir_archivo(self, filepath, nombre_drive=None, folder_id=None):
        """Sube un archivo a Google Drive"""
        if not self.service:
            return False, "No autenticado"
        
        nombre = nombre_drive or os.path.basename(filepath)
        
        # Buscar si ya existe
        query = f"name='{nombre}' and trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        results = self.service.files().list(q=query, fields='files(id)').execute()
        items = results.get('files', [])
        
        file_metadata = {'name': nombre}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(filepath, resumable=True)
        
        try:
            if items:
                # Actualizar archivo existente
                file_id = items[0]['id']
                file = self.service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media
                ).execute()
            else:
                # Crear nuevo archivo
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
            
            return True, f"Archivo subido: {file.get('id')}"
        except Exception as e:
            return False, str(e)
    
    def descargar_archivo(self, file_id, filepath):
        """Descarga un archivo de Google Drive"""
        if not self.service:
            return False
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(filepath, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            return True
        except Exception as e:
            print(f"Error descargando: {e}")
            return False
    
    def sincronizar_db(self, db_path, folder_name="Gestor_Notas_Universidad"):
        """Sincroniza la base de datos con Google Drive"""
        if not self.service:
            success, msg = self.authenticate()
            if not success:
                return False, msg
        
        # Buscar o crear carpeta
        folder_id = self.buscar_carpeta(folder_name)
        if not folder_id:
            folder_id = self.crear_carpeta(folder_name)
            if not folder_id:
                return False, "No se pudo crear la carpeta en Drive"
        
        # Subir archivo
        nombre_archivo = f"notas_backup_{os.path.basename(db_path)}"
        return self.subir_archivo(db_path, nombre_archivo, folder_id)
    
    def listar_archivos(self, folder_id=None):
        """Lista archivos en Drive"""
        if not self.service:
            return []
        
        query = "trashed=false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, modifiedTime, size)'
        ).execute()
        
        return results.get('files', [])