Pasos para Configurar Google Drive
1. Crear Proyecto en Google Cloud Console
	Ve a https://console.cloud.google.com/
	Inicia sesión con tu cuenta de Google
	Crea un nuevo proyecto (o selecciona uno existente)
	Dale un nombre, por ejemplo: "Gestor de Notas"
2. Habilitar la API de Google Drive
	En el menú lateral, ve a "APIs y servicios" → "Biblioteca"
	Busca "Google Drive API"
	Haz clic en "Habilitar"
3. Configurar Pantalla de Consentimiento OAuth
	Ve a "APIs y servicios" → "Pantalla de consentimiento de OAuth"
	Selecciona "Externo" (si no eres parte de una organización de Google Workspace)
	Completa la información básica:
	Nombre de la aplicación: "Gestor de Notas Universitarias"
	Correo electrónico de soporte: tu email
	Logo (opcional)
	En "Ámbitos", haz clic en "Agregar o quitar ámbitos"
	Busca y selecciona: https://www.googleapis.com/auth/drive.file
	Guarda y continúa
	En "Usuarios de prueba", agrega tu propio email de Google
	Guarda todo
4. Crear Credenciales OAuth 2.0
	Ve a "APIs y servicios" → "Credenciales"
	Haz clic en "Crear credenciales" → "ID de cliente de OAuth"
	Selecciona "Aplicación de escritorio" como tipo de aplicación
	Pon un nombre: "Gestor Notas Desktop"
	Haz clic en "Crear"
	Descarga el archivo JSON (se llamará algo como client_secret_xxx.json)
5. Colocar el Archivo en tu Proyecto
	Renombra el archivo descargado a credentials.json
	Colócalo en la misma carpeta donde está tu script principal (donde está main.py o tu archivo principal)