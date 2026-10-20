; Inno Setup Script for FreeFlow on Windows
; Generates FreeFlow-Setup-x64.exe or FreeFlow-Setup-arm64.exe

#define MyAppName "FreeFlow"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "BheeshamKS"
#define MyAppURL "https://github.com/BheeshamKS/FreeFlow"
#define MyAppExeName "freeflow.exe"

[Setup]
AppId={{D37D3E5B-F12E-4E61-8C53-A7851A9A9F32}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=FreeFlow-Setup-Windows
SetupIconFile=..\..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start FreeFlow automatically on login"; GroupDescription: "Startup:"

[Files]
Source: "..\..\dist\freeflow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--setup"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
