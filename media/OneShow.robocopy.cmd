@echo off
:goto :skipComments
:: % ccm_modify_date: 2024-10-05 14:17:39 %
:: % ccm_author: mpegg %
:: % ccm_version: 8 %
:: % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
:: % ccm_branch: main %
:: % ccm_object_id: create_excel_control_file.py:8 %
:: % ccm_commit_id: dbaa495ea5fbbb2a2f55cea4e3491bace9eec020 %
:: % ccm_commit_count: 8 %
:: % ccm_last_commit_message: exclude update_keywords.py from hook %
:: % ccm_last_commit_author: Matthew Pegg %
:: % ccm_last_commit_date: 2024-10-05 13:55:44 -0400 %
:: % ccm_file_last_modified: 2024-10-05 14:14:09 %
:: % ccm_file_name: create_excel_control_file.py %
:: % ccm_file_type: text/x-python %
:: % ccm_file_encoding: CRLF %
:: % ccm_file_eol: CRLF %

:skipComments

:rem this script expects arguments 

:rem source volumeGroup - eg: shows1950 
:rem source tvshow      - eg: Batman (1966) 
:rem destination VolumeGroup - eg: TTB-3T2401

:rem future enhancements
:rem destination folder      - eg: shows.TTB-3T2401

:rem enforcement rules

set "mediaRoot=C:\media.tt.omp\VG"
set "mediaVol=%1"
set "mediaShow=%~2"
set "mediaPath=%mediaRoot%\%mediaVol%\%mediaShow%"
if not exist "%mediaPath%" (
    echo "FATAL!!! - src:[%mediaPath%] not found"
    goto :ERROR1
)

set "destRoot=C:\media.tt.omp\BackupDisks"
set "destVol=%~3"

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
if "%~4"=="" (
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
    set "destDir=%~4"
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
set "logDetail=%logDir%\OneShow.robocopy.%mediaShow%.log"

set roboSwitches=/S /J /R:0 /FFT /MIN:1000000 /PURGE /NP /TEE /LOG:"%logDetail%"

robocopy "%mediaPath%" "%destPath%\%mediaShow%" %roboSwitches%
set RC=%ERRORLEVEL%
echo "%date% %time% rc:[%RC%] src:[%mediaPath%] dst:[%destPath%]" >> "%logDetail%"
echo "%date% %time% rc:[%RC%] src:[%mediaPath%] dst:[%destPath%]" >> "%logSummary%"

exit /b %RC%

:ERROR1
exit /b 64
