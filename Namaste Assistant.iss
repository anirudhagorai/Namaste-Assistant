; ======= Namaste Assistant Installer =======

[Setup]
AppId={{7F9C3A2D-4C7A-4A0E-9E7B-7F2D8E7D3B91}
AppName=Namaste Assistant
AppVersion=1.0.0
AppPublisher=Anirudha Gorai
DefaultDirName={pf}\Namaste Assistant
DefaultGroupName=Namaste Assistant
OutputDir=dist_installer
OutputBaseFilename=NamasteAssistant_Installer
SetupIconFile=assets\icon.ico
UninstallDisplayName=Namaste Assistant
UninstallDisplayIcon={app}\Namaste Assistant.exe
PrivilegesRequired=admin
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\Namaste Assistant.exe"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Icons]
Name: "{group}\Namaste Assistant"; Filename: "{app}\Namaste Assistant.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Namaste Assistant.exe"
Name: "{autodesktop}\Namaste Assistant"; Filename: "{app}\Namaste Assistant.exe"; Tasks: desktopicon; WorkingDir: "{app}"; IconFilename: "{app}\Namaste Assistant.exe"
Name: "{group}\Uninstall Namaste Assistant"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\Namaste Assistant.exe"; Description: "Launch Namaste Assistant"; Flags: nowait postinstall skipifsilent
