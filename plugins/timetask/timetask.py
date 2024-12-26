# encoding:utf-8


import plugins
import threading
import time
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from common.log import logger
from config import conf
from plugins import *

@plugins.register(
    name="timetask",
    desire_priority=77,
    hidden=False,
    desc="定时任务插件",
    version="1.0",
    author="YRRR"
)

class TimeTask(Plugin):
    def __init__(self):
        super().__init__()
        self.task_thread = None
        self.running = True
        self.tasks = []  # [(time_str, message, chat_id)]
        self.handlers[Event.TEXT] = self.handle_message
        self.load_tasks()
        self.start_task_thread()

    def load_tasks(self):
        # 从配置文件加载定时任务
        tasks = conf().get("timetask_tasks", [])
        for task in tasks:
            if isinstance(task, dict) and "time" in task and "message" in task and "chat_id" in task:
                self.tasks.append((task["time"], task["message"], task["chat_id"]))

    def start_task_thread(self):
        self.task_thread = threading.Thread(target=self.run_tasks)
        self.task_thread.daemon = True
        self.task_thread.start()

    def run_tasks(self):
        while self.running:
            current_time = time.strftime("%H:%M")
            for task_time, message, chat_id in self.tasks:
                if current_time == task_time:
                    self.send_message(message, chat_id)
            time.sleep(30)  # 每30秒检查一次

    def send_message(self, message, chat_id):
        try:
            reply = Reply(ReplyType.TEXT, message)
            e_context = Event(
                channel_id=chat_id,
                context_type=ContextType.TEXT,
                content=message
            )
            self.send(reply, e_context)
            logger.info(f"[TimeTask] 定时消息已发送: {message} 到 {chat_id}")
        except Exception as e:
            logger.error(f"[TimeTask] 发送消息失败: {e}")

    def handle_message(self, e_context: EventContext):
        if e_context.type != ContextType.TEXT:
            return

        content = e_context.content
        if not content:
            return
        
        trigger_prefix = conf().get("plugin_trigger_prefix", "$")
        if content.startswith(f"{trigger_prefix}定时任务"):
            logger.info(f"[TimeTask] 收到定时任务命令: {content}")
            try:
                # 解析消息格式：$定时任务 时间 聊天ID 消息内容
                parts = content.split(maxsplit=3)
                if len(parts) != 4:
                    raise ValueError("格式错误")
                
                time_str = parts[1]
                target_chat_id = parts[2]
                message = parts[3]
                
                # 验证时间格式
                time.strptime(time_str, "%H:%M")
                
                # 添加新任务
                self.tasks.append((time_str, message, target_chat_id))
                
                # 更新配置文件
                tasks = conf().get("timetask_tasks", [])
                tasks.append({
                    "time": time_str,
                    "message": message,
                    "chat_id": target_chat_id
                })
                conf()["timetask_tasks"] = tasks
                
                reply = Reply(ReplyType.TEXT, f"定时任务添加成功！\n时间：{time_str}\n接收ID：{target_chat_id}\n消息：{message}")
                e_context.action = EventAction.BREAK_PASS
                e_context.reply = reply
                return

            except Exception as e:
                reply = Reply(ReplyType.ERROR, f"添加定时任务失败：{str(e)}\n正确格式：{trigger_prefix}定时任务 HH:MM 聊天ID 消息内容")
                e_context.action = EventAction.BREAK_PASS
                e_context.reply = reply
                return

    def get_help_text(self, **kwargs):
        help_text = "定时任务插件使用说明:\n"
        help_text += "在配置文件中添加如下格式的配置:\n"
        help_text += '''
timetask_tasks:
  - time: "08:30"      # 24小时制的时间格式
    message: "早上好!"  # 要发送的消息内容
    chat_id: "xxx"     # 接收消息的聊天ID
'''
        return help_text

    def __del__(self):
        self.running = False
        if self.task_thread:
            self.task_thread.join()
