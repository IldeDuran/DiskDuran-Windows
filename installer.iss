; DiskDuran - Inno Setup Installer Script
; Descarga Inno Setup desde: https://jrsoftware.org/isinfo.php

[Setup]
AppName=DiskDuran
AppVersion=1.0
AppPublisher=OCiber
DefaultDirName={localappdata}\DiskDuran
DefaultGroupName=DiskDuran
OutputDir=installer_output
OutputBaseFilename=DiskDuran_Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\DiskDuran.exe
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el Escritorio"; GroupDescription: "Iconos adicionales:"; Flags: unchecked

[Files]
Source: "dist\DiskDuran\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DiskDuran"; Filename: "{app}\DiskDuran.exe"
Name: "{group}\Desinstalar DiskDuran"; Filename: "{uninstallexe}"
Name: "{autodesktop}\DiskDuran"; Filename: "{app}\DiskDuran.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DiskDuran.exe"; Description: "Ejecutar DiskDuran"; Flags: nowait postinstall skipifsilent
