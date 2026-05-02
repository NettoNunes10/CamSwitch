Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
script = folder & "\tray_app.py"
pythonExe = "C:\Users\MASSA STREAM\AppData\Local\Programs\Python\Python314\pythonw.exe"

If pythonExe = "" Then
    MsgBox "Configure o caminho do Python no launcher.", vbCritical, "CamSwitch"
    WScript.Quit 1
End If

If Not fso.FileExists(pythonExe) Then
    MsgBox "Nao encontrei o Python em: " & pythonExe, vbCritical, "CamSwitch"
    WScript.Quit 1
End If

shell.CurrentDirectory = folder
shell.Run """" & pythonExe & """ """ & script & """", 0, False
