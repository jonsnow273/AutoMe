Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -ExecutionPolicy Bypass -File ""C:\Users\Admin\Desktop\autome\run_desktop.ps1""", 0, False
