py -m venv venv
venv\Scripts\pip.exe install -r requirements.txt
venv\Scripts\pyinstaller.exe -y --onefile ^
    --collect-submodules="babel" ^
    --add-data="README;." ^
    --add-data="Lato-Light.ttf;." ^
    --add-data="Lato-Regular.ttf;." ^
    --add-data="settings.ini;." ^
    --name="Calendar Generator" ^
    --icon="calendar.ico" ^
    main.py
pause