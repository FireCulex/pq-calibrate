Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "c:\calibrations\load_hdr_profile.bat" & chr(34), 0
Set WshShell = Nothing