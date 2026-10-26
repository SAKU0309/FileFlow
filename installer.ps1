# FileFlow Installer Script
# Works on any Windows 10/11 laptop without needing Python or admin privileges.
param(
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Test-Path "$baseDir\FileFlow\FileFlow.exe") {
    $sourceDir = "$baseDir\FileFlow"
} elseif (Test-Path "$baseDir\dist\FileFlow\FileFlow.exe") {
    $sourceDir = "$baseDir\dist\FileFlow"
} elseif (Test-Path "$baseDir\FileFlow.exe") {
    $sourceDir = "$baseDir"
} else {
    $sourceDir = "$baseDir"
}

$exeSource = "$sourceDir\FileFlow.exe"
if (-not (Test-Path $exeSource)) {
    if (-not $Silent) {
        [System.Windows.Forms.MessageBox]::Show(
            "Could not find FileFlow.exe in the installation folder.`n`nPlease ensure all files were extracted properly.",
            "Installation Error",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        )
    } else {
        Write-Error "Could not find FileFlow.exe in $sourceDir"
    }
    Exit 1
}

# Target directory in LocalAppData (Standard user-level program directory, no admin required)
$targetDir = "$env:LOCALAPPDATA\Programs\FileFlow"

# 1. Close FileFlow if running
Get-Process -Name "FileFlow" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

# 2. Copy files to target directory
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

Copy-Item -Path "$sourceDir\*" -Destination $targetDir -Recurse -Force

# 3. Create Desktop and Start Menu Shortcuts via WScript.Shell
$shell = New-Object -ComObject WScript.Shell

# Desktop path (supporting OneDrive redirection)
$desktopPath = $shell.SpecialFolders.Item("Desktop")
if (-not (Test-Path $desktopPath)) {
    $desktopPath = "$env:USERPROFILE\Desktop"
}
$desktopShortcutPath = "$desktopPath\FileFlow.lnk"

$desktopShortcut = $shell.CreateShortcut($desktopShortcutPath)
$desktopShortcut.TargetPath = "$targetDir\FileFlow.exe"
$desktopShortcut.WorkingDirectory = $targetDir
$desktopShortcut.Description = "FileFlow - Effortless File Transfer Without Copy-Paste"
if (Test-Path "$targetDir\icon.ico") {
    $desktopShortcut.IconLocation = "$targetDir\icon.ico, 0"
}
$desktopShortcut.Save()

# Start Menu path
$startMenuPrograms = $shell.SpecialFolders.Item("Programs")
if (Test-Path $startMenuPrograms) {
    $startShortcutPath = "$startMenuPrograms\FileFlow.lnk"
    $startShortcut = $shell.CreateShortcut($startShortcutPath)
    $startShortcut.TargetPath = "$targetDir\FileFlow.exe"
    $startShortcut.WorkingDirectory = $targetDir
    $startShortcut.Description = "FileFlow - Effortless File Transfer Without Copy-Paste"
    if (Test-Path "$targetDir\icon.ico") {
        $startShortcut.IconLocation = "$targetDir\icon.ico, 0"
    }
    $startShortcut.Save()
}

# 4. Generate Uninstaller in target directory
$uninstallerContent = @"
@echo off
title FileFlow Uninstaller
echo Closing FileFlow if running...
taskkill /F /IM FileFlow.exe >nul 2>&1

echo Removing Shortcuts...
powershell -NoProfile -Command "`$s = New-Object -ComObject WScript.Shell; `$dt = `$s.SpecialFolders.Item('Desktop'); Remove-Item -Force `"`$dt\FileFlow.lnk`" -ErrorAction SilentlyContinue; `$sm = `$s.SpecialFolders.Item('Programs'); Remove-Item -Force `"`$sm\FileFlow.lnk`" -ErrorAction SilentlyContinue"

echo Removing FileFlow files...
cd /d "%TEMP%"
rmdir /s /q "$targetDir" >nul 2>&1

powershell -NoProfile -Command "[System.Windows.Forms.MessageBox]::Show('FileFlow has been successfully removed from your laptop.', 'FileFlow Uninstalled', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"
exit
"@

Set-Content -Path "$targetDir\Uninstall_FileFlow.bat" -Value $uninstallerContent -Encoding ASCII

# 5. Success Message & Launch
if ($Silent) {
    Write-Host "FileFlow installed successfully to $targetDir"
} else {
    $res = [System.Windows.Forms.MessageBox]::Show(
        "FileFlow has been installed successfully!`n`nShortcuts have been placed on your Desktop and Start Menu.`n`nWould you like to launch FileFlow now?",
        "Installation Complete",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Information
    )

    if ($res -eq [System.Windows.Forms.DialogResult]::Yes) {
        Start-Process "$targetDir\FileFlow.exe" -WorkingDirectory $targetDir
    }
}
