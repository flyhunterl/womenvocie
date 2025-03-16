#!/usr/bin/env python3
# encoding:utf-8

import json
import requests
import os
import time
import random
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from common.tmp_dir import TmpDir
from plugins import *

@plugins.register(
    name="WomenVoice",
    desire_priority=10,
    desc="随机御姐语音插件：发送'撒个娇'，机器人将发送随机御姐语音",
    version="1.0",
    author="AI Assistant",
)
class WomenVoice(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.config_file = os.path.join(os.path.dirname(__file__), "womenvoice_config.json")
        self.config = self.load_config()
        self.temp_files = []  # 用于跟踪临时文件
        logger.info("[WomenVoice] 插件已初始化")

    def load_config(self):
        """
        加载配置文件
        :return: 配置字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    logger.info(f"[WomenVoice] 成功加载配置文件")
                    return config
            else:
                # 创建默认配置
                default_config = {
                    "api": {
                        "url": "https://api.zxz.ee/api/sjyjsj"
                    }
                }
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"[WomenVoice] 已创建默认配置文件")
                return default_config
        except Exception as e:
            logger.error(f"[WomenVoice] 加载配置文件失败: {e}")
            return {
                "api": {
                    "url": "https://api.zxz.ee/api/sjyjsj"
                }
            }

    def get_random_voice(self):
        """
        从API获取随机御姐语音文件
        :return: 本地MP3文件路径或None（如果获取失败）
        """
        try:
            api_url = self.config["api"]["url"]
            
            for retry in range(3):
                try:
                    # 发送请求获取音频
                    response = requests.get(api_url, timeout=30)
                    response.raise_for_status()
                    break
                except requests.RequestException as e:
                    if retry == 2:
                        logger.error(f"[WomenVoice] 语音API请求失败，重试次数已用完: {e}")
                        return None
                    logger.warning(f"[WomenVoice] 语音API请求重试 {retry + 1}/3: {e}")
                    time.sleep(1)
            
            if response.status_code == 200:
                tmp_dir = TmpDir().path()
                timestamp = int(time.time())
                random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6))
                mp3_path = os.path.join(tmp_dir, f"women_voice_{timestamp}_{random_str}.mp3")
                
                with open(mp3_path, "wb") as f:
                    f.write(response.content)
                
                if os.path.getsize(mp3_path) == 0:
                    logger.error("[WomenVoice] 下载的语音文件大小为0")
                    os.remove(mp3_path)
                    return None
                
                # 将临时文件添加到跟踪列表
                self.temp_files.append(mp3_path)
                
                logger.info(f"[WomenVoice] 语音下载完成: {mp3_path}, 大小: {os.path.getsize(mp3_path)/1024:.2f}KB")
                return mp3_path
                
            else:
                logger.error(f"[WomenVoice] 语音API请求失败: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[WomenVoice] 获取语音时出错: {e}")
            if 'mp3_path' in locals() and os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                except Exception as clean_error:
                    logger.error(f"[WomenVoice] 清理失败的语音文件时出错: {clean_error}")
            return None

    def on_handle_context(self, e_context: EventContext):
        """
        处理上下文事件
        :param e_context: 事件上下文
        """
        if e_context["context"].type != ContextType.TEXT:
            return

        content = e_context["context"].content.strip()
        
        # 仅处理"撒个娇"关键词
        if content == "撒个娇":
            logger.info("[WomenVoice] 收到撒个娇请求")
            
            # 获取随机语音
            voice_path = self.get_random_voice()

            if voice_path:
                logger.info(f"[WomenVoice] 已获取语音文件: {voice_path}")

                # 发送语音消息
                reply = Reply()
                reply.type = ReplyType.VOICE
                reply.content = voice_path
                e_context["reply"] = reply

                # 阻止请求传递给其他插件
                e_context.action = EventAction.BREAK_PASS
                return True
            else:
                logger.warning("[WomenVoice] 语音获取失败")

                # 发送文本回复
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = "抱歉，随机御姐语音获取失败，请稍后再试"
                e_context["reply"] = reply

                e_context.action = EventAction.BREAK_PASS
                return True

    def get_help_text(self, **kwargs):
        """
        获取插件帮助文本
        :return: 帮助文本
        """
        help_text = "🎤 随机御姐语音插件 🎤\n\n"
        help_text += "使用方法：\n"
        help_text += "- 发送 '撒个娇' 获取一条随机御姐语音\n"
        return help_text

    def cleanup(self):
        """
        清理插件生成的临时文件
        """
        try:
            for file_path in self.temp_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.debug(f"[WomenVoice] 已清理临时文件: {file_path}")
                    except Exception as e:
                        logger.error(f"[WomenVoice] 清理临时文件失败 {file_path}: {e}")
            self.temp_files.clear()
        except Exception as e:
            logger.error(f"[WomenVoice] 清理任务异常: {e}")
