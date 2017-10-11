Python files as part of project:
1. main.py - main script for the bot. Contains all the python-telegram-bot handlers and starts the bot when executed.
2. spreadsheet.py - back end module for any functions related to google spreadsheets, which may be called by main.py


Steps for hosting the program:
1. Run the dependencies.bat (if on Windows) or dependencies.sh (if on Linux) to install all required dependencies before running the bot for the first time.
2. Change the token in the main function of main.py to your own to run your own bot
3. Delete your existing shelve files (if any)
4. Run the bot

Notes:
- DO NOT DELETE CONFIG FILE AND TERMNCONDITION.TXT IN THE NEATS-master directory!
