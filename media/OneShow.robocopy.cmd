@echo off
:goto :skipComments
:: % ccm_modify_date: 2024-10-08 21:39:56 %
:: % ccm_author: mpegg %
:: % ccm_version: 25 %
:: % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
:: % ccm_branch: main %
:: % ccm_object_id: media/OneShow.robocopy.cmd:25 %
:: % ccm_commit_id: b2a54cc00d6c06b63485f49b3b311e28586789fa %
:: % ccm_commit_count: 25 %
:: % ccm_last_commit_message: confirm latest %
:: % ccm_last_commit_author: Matthew Pegg %
:: % ccm_last_commit_date: 2024-10-08 19:34:16 -0400 %
:: % ccm_file_last_modified: 2024-10-08 21:36:45 %
:: % ccm_file_name: OneShow.robocopy.cmd %
:: % ccm_file_type: text/x-msdos-batch %
:: % ccm_file_encoding: us-ascii %
:: % ccm_file_eol: CRLF %

:skipComments

:rem this script expects arguments 

:rem source volumeGroup - eg: shows1950 
:rem source tvshow      - eg: Batman (1966) 
:rem destination VolumeGroup - eg: TTB-3T2401
:rem minSize - minimum file size
:rem maxSize - maximum file size
:rem fileExtn - file extensions
:rem destDir - destination directory (optional)

set "mediaVol=%~1"
set "mediaShow=%~2"
set "destVol=%~3"
set "minSize=%~4"
set "maxSize=%~5"
set "fileExtn=%~6"

:rem Set the root directory for destination volumes
set "destRoot=C:\media.tt.omp\BackupDisks"

:rem Set each of the three args to blank if they are -
if "%minSize%"=="-" set "minSize="
if "%maxSize%"=="-" set "maxSize="
if "%fileExtn%"=="-" set "fileExtn="

:rem Abort if there is a problem with the destVol folder
if not exist "%destRoot%\%destVol%" (
    echo "FATAL!!! - destVol folder [%destRoot%\%destVol%] not found"
    goto :ERROR1
)

:rem Check if destVol is a junction and if it is mounted
fsutil reparsepoint query "%destRoot%\%destVol%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    dir "%destRoot%\%destVol%" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo "FATAL!!! - destVol folder [%destRoot%\%destVol%] is a junction but not mounted"
        goto :ERROR1
    )
)

:rem Check if destDir is provided, if not, set default value
:rem future use - currently defaults
if "%~7"=="" (
    if "%mediaVol:~0,5%"=="shows" (
        set destDir=shows.%destVol:~0,1%%destVol:~1%
    ) else if "%mediaVol:~0,6%"=="movies" (
        set destDir=movies.%destVol:~0,1%%destVol:~1%
    ) else if "%mediaVol:~0,5%"=="music" (
        set destDir=music.%destVol:~0,1%%destVol:~1%
    ) else (
        echo FATAL!!! - unknown volume group prefix [%mediaVol%]
        goto :ERROR1
    )
    set defaultDirUsed=1
) else (
    set "destDir=%~7"
    set defaultDirUsed=0
)

set "destPath=%destRoot%\%destVol%\%destDir%"

if not exist "%destPath%" (
    if "%defaultDirUsed%"=="1" (
        mkdir "%destPath%"
        if %ERRORLEVEL% NEQ 0 (
            echo "FATAL!!! - failed to create directory [%destPath%]"
            goto :ERROR1
        )
    ) 
)
    
if not exist "%destPath%" (
    echo "FATAL!!! - destPath [%destPath%] not found"
    goto :ERROR1
)

set "logDir=C:\media.tt.omp\metadata\logs"
set "logSummary=%logDir%\OneShow.robocopy.log"
set "logDetail=%logDir%\OneShow.robocopy.%mediaVol%.%mediaShow%.log"

:rem Initialize robocopy switches
set "roboSwitches=/S /J /R:0 /FFT /NP /TEE /LOG:"%logDetail%""

:rem Add minSize switch if provided
if not "%minSize%"=="" (
    set "roboSwitches=%roboSwitches% /MIN:%minSize%"
)

:rem Add maxSize switch if provided
if not "%maxSize%"=="" (
    set "roboSwitches=%roboSwitches% /MAX:%maxSize%"
)

:rem Add PURGE switch if mediaShow is not _ALL_
if not "%mediaShow%"=="_ALL_" (
    set "roboSwitches=%roboSwitches% /PURGE"
)

:rem Add file extensions to include if provided
if not "%fileExtn%"=="" (
    set "includeFiles="
    for %%i in (%fileExtn%) do (
        set "includeFiles=!includeFiles! %%i"
    )
    set "roboSwitches=%roboSwitches% %includeFiles%"
)

if "%mediaShow%"=="_ALL_" (
    robocopy "%mediaPath%" "%destPath%" %roboSwitches%
) else (
    robocopy "%mediaPath%" "%destPath%\%mediaShow%" %roboSwitches%
)

set RC=%ERRORLEVEL%
echo "%date% %time% rc:[%RC%] src:[%mediaPath%] dst:[%destPath%]" >> "%logDetail%"
echo "%date% %time% rc:[%RC%] src:[%mediaPath%] dst:[%destPath%]" >> "%logSummary%"

exit /b %RC%

:ERROR1
exit /b 64