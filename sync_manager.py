import os
import json
import pickle
import shutil
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
import io


class SyncManager:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    SYNC_FOLDER = "GestorNotas_Sync"
    VERSION_FILE = "version.json"
    MAX_VERSIONS = 10
    
    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.folder_id = None
        
    def authenticate(self):
        """Autentica con Google Drive"""
        creds = None
        
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    return False, "No se encontró credentials.json. Configura Google Drive primero."
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
        return True, "Autenticado correctamente"
    
    def get_or_create_folder(self):
        """Obtiene o crea la carpeta de sincronización"""
        if self.folder_id:
            return self.folder_id
            
        query = f"mimeType='application/vnd.google-apps.folder' and name='{self.SYNC_FOLDER}' and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            self.folder_id = items[0]['id']
        else:
            file_metadata = {
                'name': self.SYNC_FOLDER,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            self.folder_id = file.get('id')
        
        return self.folder_id
    
    def upload_database(self, db_path, user_id="user_default"):
        """Sube la base de datos con versionado"""
        success, msg = self.authenticate()
        if not success:
            return False, msg
        
        folder_id = self.get_or_create_folder()
        
        # Verificar que el archivo existe
        if not os.path.exists(db_path):
            return False, "No se encontró la base de datos local"
        
        # Crear nombre con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"notas_{user_id}_{timestamp}.db"
        
        # Buscar versiones anteriores de este usuario
        query = f"name contains 'notas_{user_id}_' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, orderBy='name desc', fields='files(id, name, modifiedTime)').execute()
        old_files = results.get('files', [])
        
        # Subir nueva versión
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaFileUpload(db_path, resumable=True)
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, modifiedTime'
            ).execute()
            
            # Actualizar archivo de control de versiones
            version_data = {
                "latest_file": filename,
                "file_id": file.get('id'),
                "timestamp": timestamp,
                "user_id": user_id,
                "modified_time": file.get('modifiedTime')
            }
            self._update_version_file(version_data, folder_id)
            
            # Eliminar versiones antiguas (mantener últimas N)
            for old_file in old_files[self.MAX_VERSIONS:]:
                try:
                    self.service.files().delete(fileId=old_file['id']).execute()
                except:
                    pass
            
            return True, f"Sincronizado: {filename}"
            
        except Exception as e:
            return False, f"Error al subir: {str(e)}"
    
    def download_latest(self, db_path, user_id=None, backup_local=True):
        """Descarga la última versión disponible"""
        success, msg = self.authenticate()
        if not success:
            return False, msg
        
        folder_id = self.get_or_create_folder()
        
        # Construir query
        if user_id:
            query = f"name contains 'notas_{user_id}_' and '{folder_id}' in parents and trashed=false"
        else:
            query = f"name contains 'notas_' and '{folder_id}' in parents and trashed=false"
        
        results = self.service.files().list(
            q=query,
            orderBy='name desc',
            pageSize=1,
            fields='files(id, name, modifiedTime, size)'
        ).execute()
        
        files = results.get('files', [])
        if not files:
            return False, "No hay archivos para sincronizar en Drive"
        
        latest = files[0]
        file_id = latest['id']
        filename = latest['name']
        
        # Backup local antes de reemplazar
        if backup_local and os.path.exists(db_path):
            backup_name = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, backup_name)
        
        # Descargar archivo
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            with open(db_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            
            return True, f"Descargado: {filename} ({latest.get('size', '?')} bytes)"
            
        except Exception as e:
            return False, f"Error al descargar: {str(e)}"
    
    def list_versions(self, user_id=None, limit=10):
        """Lista las versiones disponibles"""
        success, msg = self.authenticate()
        if not success:
            return []
        
        folder_id = self.get_or_create_folder()
        
        if user_id:
            query = f"name contains 'notas_{user_id}_' and '{folder_id}' in parents and trashed=false"
        else:
            query = f"name contains 'notas_' and '{folder_id}' in parents and trashed=false"
        
        results = self.service.files().list(
            q=query,
            orderBy='name desc',
            pageSize=limit,
            fields='files(id, name, modifiedTime, size, createdTime)'
        ).execute()
        
        files = results.get('files', [])
        versions = []
        
        for f in files:
            # Extraer info del nombre: notas_user_timestamp.db
            parts = f['name'].replace('.db', '').split('_')
            user = parts[1] if len(parts) > 1 else 'unknown'
            timestamp = parts[2] if len(parts) > 2 else 'unknown'
            
            # Formatear fecha
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                fecha = dt.strftime("%d/%m/%Y %H:%M")
            except:
                fecha = timestamp
            
            versions.append({
                'id': f['id'],
                'filename': f['name'],
                'user': user,
                'fecha': fecha,
                'size': f.get('size', '?'),
                'modified': f.get('modifiedTime', '')
            })
        
        return versions
    
    def share_folder(self, email, role='writer'):
        """Comparte la carpeta de sincronización con otro usuario"""
        success, msg = self.authenticate()
        if not success:
            return False, msg
        
        folder_id = self.get_or_create_folder()
        
        try:
            permission = {
                'type': 'user',
                'role': role,  # 'reader' o 'writer'
                'emailAddress': email
            }
            
            self.service.permissions().create(
                fileId=folder_id,
                body=permission,
                sendNotificationEmail=True,
                fields='id'
            ).execute()
            
            return True, f"Carpeta compartida con {email} (permiso: {role})"
            
        except Exception as e:
            return False, f"Error al compartir: {str(e)}"
    
    def _update_version_file(self, version_data, folder_id):
        """Actualiza el archivo de control de versiones"""
        query = f"name='{self.VERSION_FILE}' and '{folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields='files(id)').execute()
        items = results.get('files', [])
        
        content = json.dumps(version_data, indent=2)
        
        # Usar BytesIO con MediaIoBaseUpload (no necesita archivo temporal)
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode('utf-8')),
            mimetype='application/json',
            resumable=True
        )
        
        if items:
            # Actualizar existente
            file_id = items[0]['id']
            self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            # Crear nuevo
            file_metadata = {
                'name': self.VERSION_FILE,
                'parents': [folder_id],
                'mimeType': 'application/json'
            }
            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
    
    def get_sync_status(self, db_path):
        """Compara versión local con la de Drive"""
        versions = self.list_versions(limit=1)
        if not versions:
            return "no_remote", "No hay versiones en Drive"
        
        remote = versions[0]
        remote_time = datetime.strptime(remote['fecha'], "%d/%m/%Y %H:%M")
        
        if not os.path.exists(db_path):
            return "no_local", f"Remoto: {remote['fecha']} por {remote['user']}"
        
        local_time = datetime.fromtimestamp(os.path.getmtime(db_path))
        
        if local_time > remote_time:
            return "local_newer", f"Local: {local_time.strftime('%d/%m/%Y %H:%M')} | Remoto: {remote['fecha']}"
        elif remote_time > local_time:
            return "remote_newer", f"Local: {local_time.strftime('%d/%m/%Y %H:%M')} | Remoto: {remote['fecha']}"
        else:
            return "synced", "Sincronizado"