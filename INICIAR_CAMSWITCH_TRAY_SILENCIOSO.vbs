Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
script = folder & "\tray_app.py"

Function FirstWhere(command)
    On Error Resume Next
    Set exec = shell.Exec("%ComSpec% /c where " & command)
    If Err.Number <> 0 Then
        FirstWhere = ""
        Err.Clear
        Exit Function
    End If

    output = Trim(exec.StdOut.ReadAll)
    If output = "" Then
        FirstWhere = ""
    Else
        lines = Split(output, vbCrLf)
        FirstWhere = Trim(lines(0))
    End If
End Function

pythonExe = ""

If fso.FileExists(folder & "\.venv\Scripts\pythonw.exe") Then
    pythonExe = folder & "\.venv\Scripts\pythonw.exe"
ElseIf fso.FileExists(folder & "\.venv\Scripts\python.exe") Then
    pythonExe = folder & "\.venv\Scripts\python.exe"
Else
    pythonExe = FirstWhere("pythonw.exe")
    If pythonExe = "" Then
        pythonExe = FirstWhere("python.exe")
    End If
End If

If pythonExe = "" Then
    MsgBox "Nao encontrei o Python nesta maquina. Instale o Python ou crie uma .venv neste projeto.", vbCritical, "CamSwitch"
    WScript.Quit 1
End If

shell.CurrentDirectory = folder
shell.Run """" & pythonExe & """ """ & script & """", 0, False
