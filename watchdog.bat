@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title ComfyUI 监控（带开关）

:: ======================== 用户配置区 ========================

:: 邮箱设置（换成你自己的）
set "SMTP_SERVER=smtp.qq.com"
set "SMTP_PORT=587"
set "SENDER_MAIL="
set "SENDER_PASS="
set "RECEIVER_MAIL="

:: 检测地址（默认 8188，若改过端口请修改这里）
set "CHECK_URL=http://127.0.0.1:8188"

:: ---------- 开关 ----------
:: 设为 1，首次上线自动打开浏览器；设为 0，不自动打开
set "AUTO_OPEN=1"

:: 浏览器路径（留空则调用系统默认浏览器）
set "BROWSER_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
:: ===========================================================

set "ALERT_SENT=0"
set "SOUND_FILE=C:\Windows\Media\Windows Critical Stop.wav"
set "STATE=0"
set "WAIT_CNT=0"
set "OPENED=0"

echo [%date% %time%] 监控已启动，等待 ComfyUI 上线...
if %AUTO_OPEN%==1 (echo - 自动打开浏览器：开启) else (echo - 自动打开浏览器：关闭)

:loop
curl -s -o NUL --connect-timeout 3 --max-time 5 "%CHECK_URL%" >nul 2>&1
if errorlevel 1 (
    if !STATE!==0 (
        set /a WAIT_CNT+=1
        set /a MOD=WAIT_CNT %% 6
        if !MOD!==0 echo [%date% %time%] 仍在等待连接...
    ) else (
        if !ALERT_SENT!==0 (
            echo [%date% %time%] 连接断开，触发报警。
            if exist "!SOUND_FILE!" powershell -c "(New-Object Media.SoundPlayer '!SOUND_FILE!').PlaySync()"
            call :SendMail
            set ALERT_SENT=1
        )
    )
) else (
    if !STATE!==0 (
        echo [%date% %time%] ComfyUI 已上线，进入监控状态。
        if %AUTO_OPEN%==1 if !OPENED!==0 (
            if defined BROWSER_PATH (
                start "" "!BROWSER_PATH!" "!CHECK_URL!"
            ) else (
                start "" "!CHECK_URL!"
            )
            echo [%date% %time%] 浏览器已打开。
            set OPENED=1
        )
        set STATE=1
        set ALERT_SENT=0
        set WAIT_CNT=0
    ) else (
        if !ALERT_SENT!==1 (
            echo [%date% %time%] ComfyUI 已恢复，监控重置。
            set ALERT_SENT=0
        )
    )
)
timeout /t 5 >nul
goto loop

:SendMail
powershell -Command ^
    "$EmailFrom='!SENDER_MAIL!';" ^
    "$EmailTo='!RECEIVER_MAIL!';" ^
    "$Subject='[ComfyUI 报警] 连接断开';" ^
    "$Body='ComfyUI 服务 (!CHECK_URL!) 在 !date! !time! 断开，请检查。';" ^
    "$SMTPServer='!SMTP_SERVER!';" ^
    "$SMTPPort=!SMTP_PORT!;" ^
    "$Username='!SENDER_MAIL!';" ^
    "$Password='!SENDER_PASS!';" ^
    "$msg=New-Object Net.Mail.MailMessage($EmailFrom,$EmailTo,$Subject,$Body);" ^
    "$msg.BodyEncoding=[Text.Encoding]::UTF8;" ^
    "$msg.SubjectEncoding=[Text.Encoding]::UTF8;" ^
    "$client=New-Object Net.Mail.SmtpClient($SMTPServer,$SMTPPort);" ^
    "$client.EnableSsl=$true;" ^
    "$client.Credentials=New-Object Net.NetworkCredential($Username,$Password);" ^
    "$client.Send($msg);" >nul 2>&1
goto :eof