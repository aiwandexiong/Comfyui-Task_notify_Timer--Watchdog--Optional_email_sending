"""
ComfyUI Notification Control - 设置一次，全局生效
====================================================
  一个节点整合所有声音/邮件提醒开关、成功提醒模式、自定义音频路径。
  设置后会一直保持，直到 ComfyUI 重启或你再次修改节点。

  音频格式说明：
  - Windows: 系统声用 winsound，自定义音频支持 .wav；
  - macOS: 系统声用 afplay，自定义音频支持 .aiff/.wav/.mp3 等
  - Linux: 依赖 paplay/aplay/mpg123 等，支持常见格式
"""

import os
import sys
import threading
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ============================================================
#  ✉️  邮箱配置
# ============================================================
DEFAULT_EMAIL_CFG = {
    "smtp_server":   "smtp.qq.com",
    "smtp_port":     465,
    "sender":        "",
    "password":      "",   # 授权码
    "receiver":      "",
}

# ============================================================
#  🔔  默认提醒行为（节点会覆盖这些值）
# ============================================================
DEFAULT_ENABLE_ERROR_SOUND = True
DEFAULT_ENABLE_ERROR_EMAIL = True
DEFAULT_ENABLE_SUCCESS_SOUND = True
DEFAULT_ENABLE_SUCCESS_EMAIL = False
DEFAULT_SUCCESS_NOTIFY_MODE = "all_tasks"   # "all_tasks" 或 "per_task"

# ============================================================
#  🔊  默认自定义音频文件（留空用系统音效）
# ============================================================
DEFAULT_ERROR_SOUND_FILE = r"C:\Windows\Media\Windows Critical Stop.wav"
DEFAULT_SUCCESS_SOUND_FILE = r"C:\Windows\Media\alarm03.wav"

# ============================================================
#  ⚙️  高级：是否在工作流结束后自动重置为默认值
# ============================================================
RESET_AFTER_WORKFLOW = False   # 改为 True 就会每次工作流跑完恢复默认

# ============================================================
#  内部全局状态（不要直接改，由节点控制）
# ============================================================
_error_sound_file = DEFAULT_ERROR_SOUND_FILE
_success_sound_file = DEFAULT_SUCCESS_SOUND_FILE

_enable_error_sound = DEFAULT_ENABLE_ERROR_SOUND
_enable_error_email = DEFAULT_ENABLE_ERROR_EMAIL
_enable_success_sound = DEFAULT_ENABLE_SUCCESS_SOUND
_enable_success_email = DEFAULT_ENABLE_SUCCESS_EMAIL
_success_notify_mode = DEFAULT_SUCCESS_NOTIFY_MODE

_enable_lock = threading.Lock()
_patch_installed = False
_lock = threading.Lock()

# 队列任务结果记录
_queue_task_results = []
_queue_sound_lock = threading.Lock()

# 运行时邮件配置
_email_config = {
    "enabled": False,
    "smtp_server": "",
    "smtp_port": 587,
    "sender": "",
    "password": "",
    "receiver": "",
    "use_ssl": None
}


def _apply_email_config(cfg: dict):
    """把字典配置应用到全局邮件变量"""
    global _email_config
    required = ["smtp_server", "sender", "password", "receiver"]
    if not all(cfg.get(k) for k in required):
        print("[NotifyControl] ⚠️ 邮件配置不完整，邮件通知关闭")
        _email_config["enabled"] = False
        return
    _email_config.update({
        "smtp_server": cfg["smtp_server"],
        "smtp_port": cfg.get("smtp_port", 465),
        "sender": cfg["sender"],
        "password": cfg["password"],
        "receiver": cfg["receiver"],
        "use_ssl": True if ("qq.com" in cfg["smtp_server"] or cfg.get("smtp_port") == 465) else False,
        "enabled": True,
    })
    print(f"[NotifyControl] ✅ 邮件通知已启用 → {cfg['smtp_server']} → {cfg['receiver']}")


# 启动时就用文件顶部的默认配置
_apply_email_config(DEFAULT_EMAIL_CFG)


def _send_email_safe(subject, body):
    """异步发邮件，报错只记日志"""
    cfg = _email_config
    if not cfg["enabled"]:
        return
    print(f"[NotifyControl] 📧 正在发送邮件...")
    try:
        msg = MIMEMultipart()
        msg['From'] = cfg['sender']
        msg['To'] = cfg['receiver']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        port = cfg['smtp_port']
        if cfg['use_ssl']:
            server = smtplib.SMTP_SSL(cfg['smtp_server'], port, timeout=10)
        else:
            server = smtplib.SMTP(cfg['smtp_server'], port, timeout=10)
            server.starttls()
        server.login(cfg['sender'], cfg['password'])
        server.sendmail(cfg['sender'], [cfg['receiver']], msg.as_string())
        server.quit()
        print("[NotifyControl] ✅ 邮件已发送")
    except Exception as e:
        print(f"[NotifyControl] ❌ 邮件发送失败: {e}")


# ---------- 音频播放 ----------
def _play_system_error_sound():
    print("[NotifyControl] ▶ 系统错误音")
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
        elif sys.platform == "darwin":
            subprocess.call(["afplay", "/System/Library/Sounds/Pop.aiff"])
        else:
            subprocess.call(["paplay", "/usr/share/sounds/freedesktop/stereo/dialog-error.oga"])
    except Exception as e:
        print(f"[NotifyControl] 系统音失败: {e}")


def _play_system_success_sound():
    print("[NotifyControl] ▶ 系统成功音")
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
        elif sys.platform == "darwin":
            subprocess.call(["afplay", "/System/Library/Sounds/Glass.aiff"])
        else:
            subprocess.call(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"])
    except Exception as e:
        print(f"[NotifyControl] 系统音失败: {e}")


def _play_custom_sound(filepath):
    if not os.path.exists(filepath):
        print(f"[NotifyControl] 文件不存在: {filepath}")
        return
    print(f"[NotifyControl] ▶ 自定义音频: {filepath}")
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
                print("[NotifyControl] 未找到播放器")
    except Exception as e:
        print(f"[NotifyControl] 自定义音频失败: {e}")


# ---------- 提醒触发 ----------
def _trigger_error_notification(exception=None):
    with _enable_lock:
        sound_on = _enable_error_sound
        mail_on = _enable_error_email
    if not sound_on and not mail_on:
        print("[NotifyControl] 🔇 错误提醒全部关闭")
        return

    print("[NotifyControl] ⚠️ 任务失败")
    if sound_on:
        if _error_sound_file and os.path.exists(_error_sound_file):
            _play_custom_sound(_error_sound_file)
        else:
            _play_system_error_sound()
    if mail_on and _email_config["enabled"]:
        body = f"ComfyUI 任务执行失败\n\n时间: {datetime.now()}\n错误信息: {exception}"
        threading.Thread(target=_send_email_safe, args=("ComfyUI 任务执行失败", body), daemon=True).start()


def _trigger_success_notification(task_info="任务"):
    with _enable_lock:
        sound_on = _enable_success_sound
        mail_on = _enable_success_email
    if not sound_on and not mail_on:
        return

    print("[NotifyControl] ✅ 成功提醒")
    if sound_on:
        if _success_sound_file and os.path.exists(_success_sound_file):
            _play_custom_sound(_success_sound_file)
        else:
            _play_system_success_sound()
    if mail_on and _email_config["enabled"]:
        body = f"{task_info} 已成功完成\n\n时间: {datetime.now()}"
        threading.Thread(target=_send_email_safe, args=("ComfyUI 任务执行成功", body), daemon=True).start()


# ---------- 补丁安装 ----------
def _install_all_patches():
    global _patch_installed
    with _lock:
        if _patch_installed:
            return
        try:
            import execution

            # 拦截错误
            original_get_output = execution.get_output_data
            async def _patched_get_output_data(*args, **kwargs):
                try:
                    return await original_get_output(*args, **kwargs)
                except Exception as e:
                    print(f"[NotifyControl] ⚠️ 执行错误: {e}")
                    threading.Thread(target=_trigger_error_notification, args=(e,), daemon=True).start()
                    raise
            execution.get_output_data = _patched_get_output_data
            print("[NotifyControl] ✅ 错误拦截补丁已安装")

            # 队列完成检测
            PromptQueue = execution.PromptQueue
            original_task_done = PromptQueue.task_done

            def patched_task_done(self, item_id, history_result, status, process_item=None):
                # 提前声明所有可能修改的全局变量
                global _enable_error_sound, _enable_error_email, _enable_success_sound
                global _enable_success_email, _success_notify_mode

                original_task_done(self, item_id, history_result, status, process_item)

                is_success = (
                    status is not None and
                    hasattr(status, 'status_str') and
                    status.status_str == 'success'
                )

                with _queue_sound_lock:
                    _queue_task_results.append(is_success)

                # 每任务模式立即提醒
                with _enable_lock:
                    mode = _success_notify_mode
                if is_success and mode == "per_task":
                    _trigger_success_notification("单个任务")

                # 全部任务完成时
                if self.get_tasks_remaining() == 0:
                    with _queue_sound_lock:
                        all_success = all(_queue_task_results) if _queue_task_results else False
                        _queue_task_results.clear()

                    if all_success and mode == "all_tasks":
                        _trigger_success_notification("所有队列任务")

                    # 🔁 根据配置决定是否重置（默认不再自动重置）
                    if RESET_AFTER_WORKFLOW:
                        with _enable_lock:
                            _enable_error_sound = DEFAULT_ENABLE_ERROR_SOUND
                            _enable_error_email = DEFAULT_ENABLE_ERROR_EMAIL
                            _enable_success_sound = DEFAULT_ENABLE_SUCCESS_SOUND
                            _enable_success_email = DEFAULT_ENABLE_SUCCESS_EMAIL
                            _success_notify_mode = DEFAULT_SUCCESS_NOTIFY_MODE
                        print("[NotifyControl] 🔔 提醒状态已重置为默认值")

            PromptQueue.task_done = patched_task_done
            print("[NotifyControl] ✅ 队列成功检测补丁已安装")

            _patch_installed = True
        except Exception as e:
            print(f"[NotifyControl] ❌ 补丁安装失败: {e}")
            import traceback
            traceback.print_exc()


_install_all_patches()


# ---------- 唯一的节点 ----------
class NotificationControl:
    """全局通知控制节点，输出当前设置状态字符串"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enable_error_sound": ("BOOLEAN", {"default": DEFAULT_ENABLE_ERROR_SOUND}),
                "enable_error_email": ("BOOLEAN", {"default": DEFAULT_ENABLE_ERROR_EMAIL}),
                "enable_success_sound": ("BOOLEAN", {"default": DEFAULT_ENABLE_SUCCESS_SOUND}),
                "enable_success_email": ("BOOLEAN", {"default": DEFAULT_ENABLE_SUCCESS_EMAIL}),
                "success_notify_mode": (["all_tasks", "per_task"], {"default": DEFAULT_SUCCESS_NOTIFY_MODE}),
                "error_sound_file": ("STRING", {"default": DEFAULT_ERROR_SOUND_FILE or ""}),
                "success_sound_file": ("STRING", {"default": DEFAULT_SUCCESS_SOUND_FILE or ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "execute"
    CATEGORY = "utils"
    DESCRIPTION = "设置声音/邮件提醒开关、成功提醒模式、自定义音频。修改后立即生效且保持。"

    def execute(self, enable_error_sound, enable_error_email, enable_success_sound,
                enable_success_email, success_notify_mode, error_sound_file, success_sound_file):
        global _enable_error_sound, _enable_error_email, _enable_success_sound
        global _enable_success_email, _success_notify_mode
        global _error_sound_file, _success_sound_file

        with _enable_lock:
            _enable_error_sound = enable_error_sound
            _enable_error_email = enable_error_email
            _enable_success_sound = enable_success_sound
            _enable_success_email = enable_success_email
            _success_notify_mode = success_notify_mode

        # 自定义音频路径
        if error_sound_file and os.path.exists(error_sound_file):
            _error_sound_file = error_sound_file
        else:
            _error_sound_file = DEFAULT_ERROR_SOUND_FILE if DEFAULT_ERROR_SOUND_FILE else None

        if success_sound_file and os.path.exists(success_sound_file):
            _success_sound_file = success_sound_file
        else:
            _success_sound_file = DEFAULT_SUCCESS_SOUND_FILE if DEFAULT_SUCCESS_SOUND_FILE else None

        # 生成状态字符串
        lines = [
            f"错误声音: {'开' if enable_error_sound else '关'}",
            f"错误邮件: {'开' if enable_error_email else '关'}",
            f"成功声音: {'开' if enable_success_sound else '关'}",
            f"成功邮件: {'开' if enable_success_email else '关'}",
            f"提醒模式: {success_notify_mode}",
            f"错误音频: {_error_sound_file or '系统默认'}",
            f"成功音频: {_success_sound_file or '系统默认'}",
        ]
        status_str = " | ".join(lines)
        print(f"[NotifyControl] {status_str}")
        return (status_str,)


# 节点注册
NODE_CLASS_MAPPINGS = {
    "NotificationControl": NotificationControl
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "NotificationControl": "Notification Control"
}