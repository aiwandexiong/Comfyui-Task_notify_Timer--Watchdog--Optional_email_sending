import datetime
import os
import folder_paths


class RecordTimeNode:
    """记录时间节点：每次触发都输出当前时间字符串"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "trigger": ("*",),
            }
        }

    # 强制每次执行，确保时间总是刷新
    @classmethod
    def IS_CHANGED(cls, trigger=None):
        return datetime.datetime.now().timestamp()

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("timer_record",)
    FUNCTION = "record_time"
    CATEGORY = "utils/timer"

    def record_time(self, trigger=None):
        now = datetime.datetime.now()
        return (now.isoformat(),)


class DurationCalculatorNode:
    """耗时计算节点：计算两个时间戳之差，并可保存日志"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "start_time": ("STRING", {"forceInput": True}),
                "end_time":   ("STRING", {"forceInput": True}),
                "task_name":  ("STRING", {"default": ""}),
                "log_filename": ("STRING", {"default": "时间.txt"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "calculate_duration"
    CATEGORY = "utils/timer"

    def calculate_duration(self, start_time="", end_time="", task_name="", log_filename="时间.txt"):
        # 解析时间戳
        try:
            start = datetime.datetime.fromisoformat(start_time)
            end   = datetime.datetime.fromisoformat(end_time)
        except Exception:
            return ("⚠️ 时间戳格式无效，请确认 Timer Record 节点已正确连接",)

        # 计算差
        delta = end - start
        total_seconds = int(delta.total_seconds())
        hours, rem = divmod(total_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        duration_str = f"{hours:02}时{minutes:02}分{seconds:02}秒"

        # 格式化开始时间用于日志
        start_str = start.strftime("%Y年%m月%d日%H:%M:%S")
        # 最终输出文本
        result = f"{start_str} - {task_name}\n耗时：{duration_str}"

        # 仅当 log_filename 不为空时才写入文件
        if log_filename.strip():
            output_dir = folder_paths.get_output_directory()
            log_path = os.path.join(output_dir, log_filename)
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(result + "\n")

        return (result,)


# 注册节点
NODE_CLASS_MAPPINGS = {
    "RecordTimeNode": RecordTimeNode,
    "DurationCalculatorNode": DurationCalculatorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RecordTimeNode": "Timer Record",
    "DurationCalculatorNode": "Timer Output",
}