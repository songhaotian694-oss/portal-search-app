Set shell = CreateObject("WScript.Shell")
folder = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
Set fs = CreateObject("Scripting.FileSystemObject")
exePath = folder & "dist\EmploymentPortalSearch\EmploymentPortalSearch.exe"
installingPath = folder & "dist\.portable-installing"
If fs.FileExists(exePath) And Not fs.FileExists(installingPath) Then
    command = """" & exePath & """"
    shell.Run command, 1, False
Else
    command = """" & folder & "run.bat" & """"
    shell.Run command, 1, False
End If
