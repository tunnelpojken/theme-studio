; Inno Setup script for Theme Studio. Built by build.ps1:
;   ISCC.exe /DAppVersion=0.5.0 theme-studio.iss
; Installs for the current user only (no admin prompt).
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8F3C2A51-6B0E-4D3F-9C7A-5E2B1D4A6C90}
AppName=Theme Studio
AppVersion={#AppVersion}
AppPublisher=Fested
AppPublisherURL=https://github.com/tunnelpojken/theme-studio
AppSupportURL=https://github.com/tunnelpojken/theme-studio/issues
DefaultDirName={localappdata}\Programs\Theme Studio
DefaultGroupName=Theme Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=ThemeStudio-{#AppVersion}-setup
SetupIconFile=theme-studio.ico
UninstallDisplayIcon={app}\Theme Studio.exe
UninstallDisplayName=Theme Studio
LicenseFile=..\..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "..\..\dist\Theme Studio\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Theme Studio"; Filename: "{app}\Theme Studio.exe"
Name: "{autodesktop}\Theme Studio"; Filename: "{app}\Theme Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Theme Studio.exe"; Description: "{cm:LaunchProgram,Theme Studio}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeUninstall(): Boolean;
begin
  Result := MsgBox('Uninstalling does not undo the colours, wallpaper and Terminal scheme Theme Studio applied.' + #13#10 +
                   'To get your own look back, open Theme Studio and press RESTORE ORIGINAL first.' + #13#10#13#10 +
                   'Your themes stay in %LOCALAPPDATA%\theme-studio.' + #13#10#13#10 +
                   'Uninstall Theme Studio now?', mbConfirmation, MB_YESNO) = IDYES;
end;
