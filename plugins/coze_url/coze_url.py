import re
import plugins
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *

@plugins.register(
    name="coze_url",
    desire_priority=77,
    hidden=False,
    desc="优化Coze返回结果中的图片和网址链接。",
    version="1.0",
    author="YRRR",
)
class coze_url(Plugin):
    def __init__(self):
        super().__init__()
        try:
            self.handlers[Event.ON_DECORATE_REPLY] = self.on_decorate_reply
            logger.info("[coze_url] inited.")
        except Exception as e:
            logger.warn("[coze_url] init failed, ignore.")
            raise e

    def on_decorate_reply(self, e_context: EventContext):
        if e_context["reply"].type != ReplyType.TEXT:
            return
        try:
            channel = e_context["channel"]
            context = e_context["context"]
            content = e_context["reply"].content.strip()

            # 避免图片无法下载时，重复调用插件导致没有响应的问题
            if content.startswith("[DOWNLOAD_ERROR]"):
                return

            # 处理带有签名参数的图片 URL（针对 byteimg.com 类型的图片链接）
            byteimg_image_link_pattern = r"(https://[a-zA-Z0-9-]+-bot-workflow-sign\.byteimg\.com/tos-cn-i-[a-zA-Z0-9]+/[a-zA-Z0-9]+\.png~tplv-[a-zA-Z0-9-]+-image\.png\?rk3s=[a-zA-Z0-9]+&x-expires=[0-9]+&x-signature=[a-zA-Z0-9%]+)"
            byteimg_matches = re.findall(byteimg_image_link_pattern, content)

            if byteimg_matches:
                unique_byteimg_matches = list(dict.fromkeys(byteimg_matches))
                for url in unique_byteimg_matches:
                    reply = Reply(ReplyType.IMAGE_URL, url)
                    channel.send(reply, context)
                # 移除内容中的 byteimg 图片链接，确保保留查询参数
                content = re.sub(byteimg_image_link_pattern, '', content).strip()

            # 只提取 .png 类型的图片链接
            png_image_url_pattern = r"(https?://[^\s]+\.png)"
            png_matches = re.findall(png_image_url_pattern, content)

            # 如果找到 PNG 链接，处理为图片，并移除链接
            if png_matches:
                # 使用 set 去重并保留顺序
                unique_png_matches = list(dict.fromkeys(png_matches))  # 使用 dict.fromkeys 保持顺序并去重
                replies = [Reply(ReplyType.IMAGE_URL, url) for url in unique_png_matches]
                logger.info(f"[coze_url] found {len(replies)} unique .png images.")
                for reply in replies:
                    channel.send(reply, context)  # 发送图片链接

                # 移除内容中的 .png 链接
                content = re.sub(png_image_url_pattern, '', content).strip()

            # 处理 Coze 链接为图片
            coze_image_link_pattern = r"(https?://s\.coze\.cn/t/[^\s]+)"
            coze_matches = re.findall(coze_image_link_pattern, content)

            # 如果找到 Coze 链接，尝试将其处理为图片
            if coze_matches:
                # 使用 dict.fromkeys 去重并保留顺序
                unique_coze_matches = list(dict.fromkeys(coze_matches))
                for url in unique_coze_matches:
                    # 发送链接为图片
                    reply = Reply(ReplyType.IMAGE_URL, url)
                    channel.send(reply, context)
                # 移除内容中的 Coze 链接
                content = re.sub(coze_image_link_pattern, '', content).strip()

            # 处理新的图片链接格式
            new_image_link_pattern = r"(https?://[^\s]+\.png(~tplv-[^\s]+)?(\?.*)?)"
            new_image_matches = re.findall(new_image_link_pattern, content)

            # 如果找到新的图片链接，处理为图片
            if new_image_matches:
                unique_new_image_matches = list(dict.fromkeys([match[0] for match in new_image_matches]))
                for url in unique_new_image_matches:
                    reply = Reply(ReplyType.IMAGE_URL, url)
                    channel.send(reply, context)
                # 移除内容中的新图片链接
                content = re.sub(new_image_link_pattern, '', content).strip()

            # 处理重复链接的情况
            content = re.sub(r"(https?://[^\s]+)\1+", r"\1", content)  # 替换连续重复的链接为一个链接

            # 去掉每行结尾的Markdown链接中网址部分的小括号，避免微信误以为“)”是网址的一部分导致微信中无法打开该页面
            content_list = content.split('\n')
            new_content_list = [re.sub(r'\((https?://[^\s]+)\)$', r' \1', line) for line in content_list]
            if new_content_list != content_list:
                logger.info(f"[coze_url] parenthesis in the url has been removed, content={content}")
                reply = Reply(ReplyType.TEXT, '\n'.join(new_content_list).strip())
                e_context["reply"] = reply  # 保留并输出修改后的文本内容
            else:
                e_context["reply"].content = content  # 输出处理后的文本内容

        except Exception as e:
            logger.warn(f"[coze_url] on_decorate_reply failed, content={content}, error={e}")
        finally:
            e_context.action = EventAction.CONTINUE  # 确保其他内容不会被阻止

    def get_help_text(self, **kwargs):
        return "优化Coze返回结果中的图片和网址链接。"
