; Dayline per-user installer (no admin). Built by:
;   ISCC /DAppVersion=<ver> /DDistDir=<abs path to dist\Dayline> packaging\installer.iss
; Uninstall removes program files only — vault, %APPDATA%\Dayline and
; %LOCALAPPDATA%\Dayline are never touched.

#define MyAppName "Dayline"
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef DistDir
  #define DistDir "..\dist\Dayline"
#endif

[Setup]
AppId={{8D9E2B4F-6C1A-4E7D-9F0B-2A5C7E1D3B90}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher=Dayline
DefaultDirName={localappdata}\Programs\Dayline
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=Dayline-Setup-{#AppVersion}
SetupIconFile=..\src\dayline\ui\assets\app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Dayline.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Dayline.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Dayline.exe"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Intentionally EMPTY: never delete user data, settings, logs or backups.
