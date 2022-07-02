@echo off 
>NUL powershell New-Item -Path .\.vscode -ItemType Directory
>NUL powershell New-Item .\.vscode\settings.json
>NUL powershell Set-Content .\.vscode\settings.json '{\"python.terminal.activateEnvironment\": true, \"python.terminal.activateEnvInCurrentTerminal\": true, \"python.defaultInterpreterPath\": \"~/.%1/bin/python\"}' 
python -m venv .%1 && .%1\Scripts\activate.bat && python -m pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
