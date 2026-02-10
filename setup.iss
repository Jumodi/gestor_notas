[Setup]
AppName=Gestor de Notas
AppVersion=1.0
DefaultDirName={pf}\Gestor de Notas
DefaultGroupName=Gestor de Notas
OutputDir=installer
OutputBaseFilename=GestorNotas_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: spanish; MessagesFile: compiler:Languages\Spanish.isl

[Tasks]
Name: desktopicon; Description: Crear icono en el escritorio; GroupDescription: Iconos adicionales:; Flags: unchecked

[Dirs]
Name: "{app}\data"

[Files]
Source: "dist\GestorNotas.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Gestor de Notas"; Filename: "{app}\GestorNotas.exe"
Name: "{autodesktop}\Gestor de Notas"; Filename: "{app}\GestorNotas.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\GestorNotas.exe"; Description: Ejecutar Gestor de Notas; Flags: nowait postinstall skipifsilent