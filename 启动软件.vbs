Set shell = CreateObject("WScript.Shell")
folder = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
Set fs = CreateObject("Scripting.FileSystemObject")
exePath = folder & "dist\EmploymentPortalSearch\EmploymentPortalSearch.exe"
If fs.FileExists(exePath) Then
    command = """" & exePath & """"
Else
    command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & folder & "run.ps1"""
End If
exitCode = shell.Run(command, 0, True)
If exitCode <> 0 Then
    MsgBox "Startup failed. Please check data\logs.", vbCritical, "Employment Portal Search"
End If
