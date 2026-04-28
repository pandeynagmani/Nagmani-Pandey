; SANT Digital Solution - School ERP Installer Script
; Inno Setup Script (.iss)
; Run with Inno Setup Compiler to create Setup.exe

[Setup]
AppName=Maa Kamala Public School ERP
AppVersion=1.0.0
AppPublisher=Sant Digital Solution
AppPublisherURL=https://santdigitalsolution.com
DefaultDirName={autopf}\SchoolERP
DefaultGroupName=Maa Kamala Public School ERP
OutputDir=Output
OutputBaseFilename=SchoolERP_Setup
SetupIconFile=
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"
Name: "autostart"; Description: "Start ERP server automatically on Windows boot"; GroupDescription: "System settings:"

[Files]
; Include the entire PyInstaller output directory
Source: "..\dist\SchoolERP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start menu shortcut
Name: "{group}\Maa Kamala Public School ERP"; Filename: "{app}\SchoolERP.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall School ERP"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\Maa Kamala Public School ERP"; Filename: "{app}\SchoolERP.exe"; WorkingDir: "{app}"; Tasks: desktopicon

; Auto-start on boot
Name: "{userstartup}\SchoolERP"; Filename: "{app}\SchoolERP.exe"; WorkingDir: "{app}"; Tasks: autostart

[Run]
; Launch after installation
Filename: "{app}\SchoolERP.exe"; Description: "Launch School ERP now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up data directory on uninstall (optional - user can choose)
Type: filesandordirs; Name: "{app}\data"

[Code]
// Custom code to show connection info after install
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox(
      'Installation Complete!' + #13#10 + #13#10 +
      'Default Login Credentials:' + #13#10 +
      '  Username: principal' + #13#10 +
      '  Password: admin123' + #13#10 + #13#10 +
      'The ERP server will start automatically.' + #13#10 +
      'Other devices on the same Wi-Fi can connect' + #13#10 +
      'using the Network URL shown in the console.' + #13#10 + #13#10 +
      'Developed by Sant Digital Solution',
      mbInformation, MB_OK
    );
  end;
end;
