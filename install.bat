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
set "AGENTS_DIR=%USERPROFILE%\.agents"

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
if not exist "%AGENTS_DIR%\skills\%SKILL_NAME%" mkdir "%AGENTS_DIR%\skills\%SKILL_NAME%"
echo   Directories ready

:: Step 4: Install skill files
echo [4/6] Installing skill files...
copy /Y "%REPO_DIR%SKILL.md" "%AGENTS_DIR%\skills\%SKILL_NAME%\" >nul

if exist "%REPO_DIR%prompts" (
    xcopy /E /I /Y "%REPO_DIR%prompts" "%AGENTS_DIR%\skills\%SKILL_NAME%\prompts" >nul
)
if exist "%REPO_DIR%templates" (
    xcopy /E /I /Y "%REPO_DIR%templates" "%AGENTS_DIR%\skills\%SKILL_NAME%\templates" >nul
)
if exist "%REPO_DIR%spec" (
    xcopy /E /I /Y "%REPO_DIR%spec" "%AGENTS_DIR%\skills\%SKILL_NAME%\spec" >nul
)
if exist "%REPO_DIR%scripts" (
    xcopy /E /I /Y "%REPO_DIR%scripts" "%AGENTS_DIR%\skills\%SKILL_NAME%\scripts" >nul
)

:: Create symlink (requires admin on Windows, fallback to copy)
mklink /D "%CLAUDE_DIR%\skills\%SKILL_NAME%" "%AGENTS_DIR%\skills\%SKILL_NAME%" >nul 2>&1
if %errorlevel% neq 0 (
    echo   Symlink failed (admin may be needed), copying instead...
    xcopy /E /I /Y "%AGENTS_DIR%\skills\%SKILL_NAME%" "%CLAUDE_DIR%\skills\%SKILL_NAME%" >nul
)

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

if exist "%AGENTS_DIR%\skills\%SKILL_NAME%\SKILL.md" (
    echo   SKILL.md: OK
) else (
    echo   SKILL.md: MISSING
    set /a ERRORS+=1
)

if exist "%CLAUDE_DIR%\agents\ctf-reviewer.md" (
    echo   ctf-reviewer agent: OK
) else (
    echo   ctf-reviewer agent: MISSING
    set /a ERRORS+=1
)

echo.
if !ERRORS! equ 0 (
    echo ========================================
    echo   Installation Successful!
    echo ========================================
    echo.
    echo Installed components:
    echo   Skill:   ctf-challenge-creator
    echo   Agent:   ctf-reviewer
    echo   Templates: %AGENTS_DIR%\skills\%SKILL_NAME%\templates\
    echo.
    echo Usage: Just say 'Create a Web SSTI Easy challenge' to start!
) else (
    echo Installation completed with !ERRORS! error(s).
    pause
    exit /b 1
)

endlocal
