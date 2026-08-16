@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   CTF Challenge Creator Skill Installer
echo ========================================
echo.

set "SKILL_NAME=ctf-challenge-creator"
set "REPO_DIR=%~dp0"
set "CLAUDE_DIR=%USERPROFILE%\.claude"
set "CODEX_DIR=%USERPROFILE%\.codex"

:: Step 1: Check Docker
echo [1/6] Checking Docker...
where docker >nul 2>&1
if %errorlevel% equ 0 (
    docker --version 2>nul
    echo   Docker: found
) else (
    echo   WARNING: Docker not found. Docker-based challenge testing will not work.
)

:: Step 2: Check Docker Compose
echo [2/6] Checking Docker Compose...
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    echo   Docker Compose: available
) else (
    echo   WARNING: docker compose not found.
)

:: Step 3: Create directories
echo [3/6] Creating directories...
if not exist "%CLAUDE_DIR%\skills" mkdir "%CLAUDE_DIR%\skills"
if not exist "%CLAUDE_DIR%\agents" mkdir "%CLAUDE_DIR%\agents"
if not exist "%CODEX_DIR%\skills" mkdir "%CODEX_DIR%\skills"
echo   Directories ready

:: Step 4: Install skill files
echo [4/6] Installing skill files...
if exist "%USERPROFILE%\.agents\skills\%SKILL_NAME%" rmdir /S /Q "%USERPROFILE%\.agents\skills\%SKILL_NAME%"
if exist "%CODEX_DIR%\skills\%SKILL_NAME%" rmdir /S /Q "%CODEX_DIR%\skills\%SKILL_NAME%"
if exist "%CLAUDE_DIR%\skills\%SKILL_NAME%" rmdir /S /Q "%CLAUDE_DIR%\skills\%SKILL_NAME%"
mklink /J "%CODEX_DIR%\skills\%SKILL_NAME%" "%REPO_DIR%" >nul
if errorlevel 1 goto :install_failed
mklink /J "%CLAUDE_DIR%\skills\%SKILL_NAME%" "%REPO_DIR%" >nul
if errorlevel 1 goto :install_failed

echo   Skill files installed

:: Step 5: Install agents
echo [5/6] Installing agent definitions...
for %%f in ("%REPO_DIR%agents\*.md") do (
    copy /Y "%%f" "%CLAUDE_DIR%\agents\" >nul
    echo   Agent: %%~nxf
)
echo   Agent definitions installed

:: Step 6: Verify
echo [6/6] Verifying installation...
set ERRORS=0

if exist "%CLAUDE_DIR%\agents\ctf-reviewer.md" (
    echo   ctf-reviewer agent: OK
) else (
    echo   ctf-reviewer agent: MISSING
    set /a ERRORS+=1
)

if exist "%CODEX_DIR%\skills\%SKILL_NAME%\SKILL.md" (
    echo   Codex SKILL.md: OK
) else (
    echo   Codex SKILL.md: MISSING
    set /a ERRORS+=1
)

echo.
if not "!ERRORS!"=="0" goto :install_failed

echo ========================================
echo   Installation Successful
echo ========================================
echo.
echo Installed components:
echo   Source:  %REPO_DIR%
echo   Codex:   %CODEX_DIR%\skills\%SKILL_NAME%\ ^(junction^)
echo   Claude:  %CLAUDE_DIR%\skills\%SKILL_NAME%\ ^(junction^)
echo   Agent:   ctf-reviewer
echo   Templates: %REPO_DIR%templates\
echo.
echo Usage: Just say 'Create a Web SSTI Easy challenge' to start
goto :install_done

:install_failed
echo Installation completed with !ERRORS! error(s).
pause
exit /b 1

:install_done

endlocal
