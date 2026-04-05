[Setup]
AppId={{D2FB4B62-DA2F-4E30-9CE0-0E1B55EB90B3}
AppName=Media Duplicatie Finder
AppVersion=2026-April
AppPublisher=RymndA
AppPublisherURL=https://github.com/Rymnda/MediaDuplicatieFinder
AppSupportURL=https://github.com/Rymnda/MediaDuplicatieFinder
AppUpdatesURL=https://github.com/Rymnda/MediaDuplicatieFinder
DefaultDirName={localappdata}\Programs\Media Duplicatie Finder
DefaultGroupName=Media Duplicatie Finder
DisableProgramGroupPage=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=MediaDuplicatieFinder_Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\MediaDuplicatieFinder.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardImageFile=Logo_background.jpg
WizardSmallImageFile=Logo_background.jpg
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "dist\MediaDuplicatieFinder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Media Duplicatie Finder"; Filename: "{app}\MediaDuplicatieFinder.exe"
Name: "{autodesktop}\Media Duplicatie Finder"; Filename: "{app}\MediaDuplicatieFinder.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MediaDuplicatieFinder.exe"; Description: "Launch Media Duplicatie Finder"; Flags: nowait postinstall skipifsilent
