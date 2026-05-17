@echo off
cd /d "%~dp0"
REM mfa_tool.py will use `mfa` from PATH, or fall back to `conda run -n mfa mfa`.
REM If your MFA environment has another name, run: set MFA_CONDA_ENV=your_env
python -m pip install -r requirements.txt
python mfa_tool.py %*
echo.
echo 完成。最终 TextGrid 在 result 文件夹中。
pause
