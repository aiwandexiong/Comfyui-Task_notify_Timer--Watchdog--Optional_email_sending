
import os, sys, threading, subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ============================================================
#  ✉️  邮箱配置区（直接填写，无需环境变量）
# ============================================================
EMAIL_CFG = {
    "smtp_server":   "smtp.qq.com",          # SMTP 服务器
    "smtp_port":     465,                    # 端口 465 或 587 均可
    "sender":        "",      # 发件邮箱
    "password":      "",           # QQ 邮箱请填写授权码，不是登录密码！
    "receiver":      "",      # 收件邮箱
}
# ============================================================

# ---------- 全局变量 ----------
_error_sound_file = "C:\Windows\Media\Windows Critical Stop.wav"          # 自定义错误音路径，None 使用系统音
_success_sound_file = None        # 自定义成功音路径，None 使用系统音
_patch_installed = False
_lock = threading.Lock()

# 队列任务结果记录（用于成功检测）
_queue_task_results = []
_queue_sound_lock = threading.Lock()

# ---------- 邮件配置 ----------
_email_config = {
    "enabled": True,
    "smtp_server": "",
    "smtp_port": 587,
    "sender": "",
    "password": "",
    "receiver": "",
    "use_ssl": None
}

def _load_email_config():
    """读取邮件配置：优先环境变量，否则使用 EMAIL_CFG"""
    global _email_config

    env_server = os.environ.get("COMFYUI_ERROR_EMAIL_SMTP_SERVER", "")
    env_port   = os.environ.get("COMFYUI_ERROR_EMAIL_SMTP_PORT", "")
    env_sender = os.environ.get("COMFYUI_ERROR_EMAIL_SENDER", "")
    env_pwd    = os.environ.get("COMFYUI_ERROR_EMAIL_PASSWORD", "")
    env_recv   = os.environ.get("COMFYUI_ERROR_EMAIL_RECEIVER", "")
    env_ssl    = os.environ.get("COMFYUI_ERROR_EMAIL_USE_SSL", "").lower()

    env_ready = all([env_server, env_sender, env_pwd, env_recv])

    if env_ready:
        _email_config["smtp_server"] = env_server
        _email_config["sender"] = env_sender
        _email_config["password"] = env_pwd
        _email_config["receiver"] = env_recv
        if env_port:
            try:
                _email_config["smtp_port"] = int(env_port)
            except:
                pass
        if env_ssl in ("true", "false"):
            _email_config["use_ssl"] = (env_ssl == "true")
        print("[ErrorSound] 📧 使用环境变量邮件配置")
    else:
        cfg = EMAIL_CFG
        if cfg["smtp_server"] and cfg["sender"] and cfg["password"] and cfg["receiver"]:
            _email_config["smtp_server"] = cfg["smtp_server"]
            _email_config["smtp_port"]   = cfg.get("smtp_port", 465)
            _email_config["sender"]      = cfg["sender"]
            _email_config["password"]    = cfg["password"]
            _email_config["receiver"]    = cfg["receiver"]
            _email_config["use_ssl"]     = None
            print("[ErrorSound] 📧 使用代码内默认邮件配置")
        else:
            print("[ErrorSound] ⚠️ 邮件配置不完整，请检查 EMAIL_CFG 字典")
            _email_config["enabled"] = False
            return

    if not (_email_config["smtp_server"] and _email_config["sender"] and
            _email_config["password"] and _email_config["receiver"]):
        print("[ErrorSound] ❌ 邮件关键字段缺失，通知未启用")
        _email_config["enabled"] = False
        return

    _email_config["enabled"] = True
    print(f"[ErrorSound] ✅ 邮件通知已启用 → {_email_config['smtp_server']}:{_email_config['smtp_port']} → {_email_config['receiver']}")

_load_email_config()

def _send_email_safe(subject, body):
    """发送邮件（自动 SSL/STARTTLS）"""
    cfg = _email_config
    if not cfg["enabled"]:
        return
    print(f"[ErrorSound] 📧 正在发送邮件...")
    try:
        msg = MIMEMultipart()
        msg['From'] = cfg['sender']
        msg['To'] = cfg['receiver']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        port = cfg['smtp_port']
        use_ssl = cfg['use_ssl']
        if use_ssl is None:
            if "qq.com" in cfg['smtp_server']:
                use_ssl = True
            else:
                use_ssl = (port == 465)
        if use_ssl:
            print(f"[ErrorSound] ↪ SMTP_SSL {cfg['smtp_server']}:{port}")
            server = smtplib.SMTP_SSL(cfg['smtp_server'], port, timeout=10)
        else:
            print(f"[ErrorSound] ↪ SMTP+STARTTLS {cfg['smtp_server']}:{port}")
            server = smtplib.SMTP(cfg['smtp_server'], port, timeout=10)
            server.starttls()
        server.login(cfg['sender'], cfg['password'])
        server.sendmail(cfg['sender'], [cfg['receiver']], msg.as_string())
        server.quit()
        print("[ErrorSound] ✅ 邮件已发送")
    except Exception as e:
        print(f"[ErrorSound] ❌ 邮件发送失败: {e}")

# ---------- 音频播放函数 ----------
def _play_system_error_sound():
    print("[ErrorSound] ▶ 播放系统错误音")
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
        elif sys.platform == "darwin":
            subprocess.call(["afplay", "/System/Library/Sounds/Pop.aiff"])
        else:
            try:
                subprocess.call(["paplay", "/usr/share/sounds/freedesktop/stereo/dialog-error.oga"])
            except:
                print("[ErrorSound] ❌ 无法播放系统音")
    except Exception as e:
        print(f"[ErrorSound] ❌ 系统音播放失败: {e}")

def _play_system_success_sound():
    print("[ErrorSound] ▶ 播放系统成功音")
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
        elif sys.platform == "darwin":
            subprocess.call(["afplay", "/System/Library/Sounds/Glass.aiff"])
        else:
            try:
                subprocess.call(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"])
            except:
                print("[ErrorSound] ❌ 无法播放系统成功音")
    except Exception as e:
        print(f"[ErrorSound] ❌ 系统成功音播放失败: {e}")

def _play_custom_sound(filepath):
    if not os.path.exists(filepath):
        print(f"[ErrorSound] ❌ 文件不存在: {filepath}")
        return
    print(f"[ErrorSound] ▶ 播放自定义音频: {filepath}")
    try:
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            return
        except ImportError:
            pass
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME)
        elif sys.platform == "darwin":
            subprocess.call(["afplay", filepath])
        else:
            for cmd in ["paplay", "aplay", "mpg123", "play"]:
                if subprocess.call(["which", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0:
                    subprocess.call([cmd, filepath])
                    break
            else:
                print("[ErrorSound] ❌ 未找到播放器")
    except Exception as e:
        print(f"[ErrorSound] ❌ 自定义音频播放失败: {e}")

# ---------- 错误处理回调（单体错误时调用） ----------
def _on_prompt_error(exception=None):
    print("[ErrorSound] ⚠️ 检测到任务失败")
    if _error_sound_file:
        _play_custom_sound(_error_sound_file)
    else:
        _play_system_error_sound()
    if _email_config["enabled"]:
        body = f"ComfyUI 任务执行失败\n\n时间: {datetime.now()}\n错误信息: {exception}"
        threading.Thread(target=_send_email_safe, args=("ComfyUI 任务执行失败", body), daemon=True).start()

# ---------- 成功提示播放 ----------
def _play_success_sound():
    if _success_sound_file and os.path.exists(_success_sound_file):
        _play_custom_sound(_success_sound_file)
    else:
        _play_system_success_sound()

# ---------- 补丁安装（错误拦截 + 队列成功检测）----------
def _install_all_patches():
    global _patch_installed
    with _lock:
        if _patch_installed:
            return
        try:
            import execution

            # 1. 错误拦截补丁（保留原有功能）
            original_get_output = execution.get_output_data
            async def _patched_get_output_data(*args, **kwargs):
                try:
                    return await original_get_output(*args, **kwargs)
                except Exception as e:
                    print(f"[ErrorSound] ⚠️ 任务执行错误: {e}")
                    threading.Thread(target=_on_prompt_error, args=(e,), daemon=True).start()
                    raise
            execution.get_output_data = _patched_get_output_data
            print("[ErrorSound] ✅ 错误拦截补丁已安装")

            # 2. 队列全部成功检测补丁
            PromptQueue = execution.PromptQueue
            original_task_done = PromptQueue.task_done

            def patched_task_done(self, item_id, history_result, status, process_item=None):
                # 调用原始方法
                original_task_done(self, item_id, history_result, status, process_item)
                # 记录本任务是否成功
                with _queue_sound_lock:
                    is_success = (
                        status is not None and
                        hasattr(status, 'status_str') and
                        status.status_str == 'success'
                    )
                    _queue_task_results.append(is_success)
                # 检查队列是否完全空闲
                if self.get_tasks_remaining() == 0:
                    with _queue_sound_lock:
                        if _queue_task_results and all(_queue_task_results):
                            print("[ErrorSound] ✅ 所有队列任务已完成且全部成功，播放成功提示音")
                            threading.Thread(target=_play_success_sound, daemon=True).start()
                        else:
                            print("[ErrorSound] ℹ️ 队列任务已完成，但存在失败项（或队列结果为空），不播放成功音")
                        _queue_task_results.clear()

            PromptQueue.task_done = patched_task_done
            print("[ErrorSound] ✅ 队列成功检测补丁已安装")

            _patch_installed = True
        except Exception as e:
            print(f"[ErrorSound] ❌ 补丁安装失败: {e}")
            import traceback
            traceback.print_exc()

_install_all_patches()

# ---------- 自定义节点 ----------
class ErrorSoundPassthrough:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "signal": ("*", {}),
                "enable": ("BOOLEAN", {"default": True}),
                "error_sound_file": ("STRING", {"default": ""}),
                "success_sound_file": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ("*",)
    FUNCTION = "execute"
    CATEGORY = "utils"

    def execute(self, signal, enable, error_sound_file, success_sound_file):
        global _error_sound_file, _success_sound_file
        if enable:
            if error_sound_file and os.path.exists(error_sound_file):
                _error_sound_file = error_sound_file
                print(f"[ErrorSound] ✅ 自定义错误提示音: {error_sound_file}")
            else:
                _error_sound_file = None
                print("[ErrorSound] ℹ️ 使用系统默认错误提示音")

            if success_sound_file and os.path.exists(success_sound_file):
                _success_sound_file = success_sound_file
                print(f"[ErrorSound] ✅ 自定义成功提示音: {success_sound_file}")
            else:
                _success_sound_file = None
                print("[ErrorSound] ℹ️ 使用系统默认成功提示音")
        else:
            _error_sound_file = None
            _success_sound_file = None
            print("[ErrorSound] ℹ️ 已重置为系统默认提示音")
        return (signal,)

class ErrorEmailConfig:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "signal": ("*", {}),
                "enable": ("BOOLEAN", {"default": False}),
                "smtp_server": ("STRING", {"default": ""}),
                "smtp_port": ("INT", {"default": 587}),
                "sender": ("STRING", {"default": ""}),
                "password": ("STRING", {"default": ""}),
                "receiver": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ("*",)
    FUNCTION = "execute"
    CATEGORY = "utils"

    def execute(self, signal, enable, smtp_server, smtp_port, sender, password, receiver):
        global _email_config
        if enable and smtp_server and sender and password and receiver:
            _email_config.update({
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "sender": sender,
                "password": password,
                "receiver": receiver,
                "enabled": True,
                "use_ssl": None
            })
            print("[ErrorSound] ✅ 邮件已通过节点配置")
        else:
            _email_config["enabled"] = False
            print("[ErrorSound] ℹ️ 邮件节点禁用或信息不全")
        return (signal,)

NODE_CLASS_MAPPINGS = {
    "ErrorSoundPassthrough": ErrorSoundPassthrough,
    "ErrorEmailConfig": ErrorEmailConfig
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ErrorSoundPassthrough": "Error Sound (With Success)",
    "ErrorEmailConfig": "Error Email (Config)"
}