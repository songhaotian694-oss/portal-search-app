Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
desktop = shell.SpecialFolders("Desktop")
Set shortcut = shell.CreateShortcut(fs.BuildPath(desktop, "选调生信息搜索.lnk"))
exePath = fs.BuildPath(folder, "dist\EmploymentPortalSearch\EmploymentPortalSearch.exe")
If fs.FileExists(exePath) Then
    shortcut.TargetPath = exePath
Else
    shortcut.TargetPath = fs.BuildPath(folder, "启动软件.vbs")
End If
shortcut.WorkingDirectory = folder
shortcut.IconLocation = fs.BuildPath(folder, "assets\app-icon.ico") & ",0"
shortcut.Description = "打开选调生信息搜索软件"
shortcut.Save
MsgBox "桌面快捷方式已创建。", vbInformation, "选调生信息搜索"
