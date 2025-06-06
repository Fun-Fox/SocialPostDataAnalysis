import datetime
import html
import os
import re

__all__ = ["social_assessor_assistant"]

from typing import Any

from agent import get_logger
from agent.flow import context_research_flow, social_assessor_flow

def extract_time_from_filename(filename: str) -> str:
    """从文件名中提取时间部分，格式如：2024-11-12 02-25-img_74.jpg"""
    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}-\d{2})', filename)
    if match:
        raw_time = match.group(1)
        # 替换 "-" 为 ":"，转换成更标准的时间格式
        return raw_time.replace('-', ':').replace(':', '-', 2)
    return "unknown_time"


def social_assessor_assistant(user_name, create_time, input_content, logger, context=""):
    try:

        if context == "":
            # 背景调查信息
            research_shared = {
                "user_name": user_name, "create_time": create_time, "post": input_content, "logger": logger
            }
            context_agent_flow = context_research_flow()
            context_agent_flow.run(research_shared)

            context = research_shared.get("context", "内容未分析完成")

        logger.info(f"\n ---开始结合背景调查信息进行内容分析--- \n 背景：\n {context}")

        social_shared = {
            "post": input_content, "context": f"内容背景：\n{context}", "logger": logger
        }
        social_agent_flow = social_assessor_flow()
        social_agent_flow.run(social_shared)

        post_evaluate = social_shared.get("post_evaluate", "内容未分析完成")

        logger.info(f"[Agent任务完成]-[DONE]: \n {post_evaluate} ")
        return post_evaluate, context
    except Exception as e:
        logger.error(f"内容分析出现异常: {e}")
        return "内容分析出现异常。", context


def build_input_content(text_content: str, video_content: str = None) -> str:
    content_parts = ["帖子文本内容：", text_content]

    if video_content:
        content_parts.append("")  # 添加空行作为分隔
        content_parts.extend(["帖子视听文本数据：", video_content])

    return "\n".join(content_parts)


if __name__ == "__main__":
    # 示例输入内容（video_content 可为空）
    text_content = """
    GET OUT &amp; VOTE EARLY! https://t.co/LCHQU6zUsZ https://t.co/0dndZGXSIN
    """
    # 使用正则表达式移除链接
    cleaned_text = re.sub(r'https?://\S+', '', text_content)
    decoded_text = html.unescape(cleaned_text.strip())

    video_content = """
    Folks, it's time for another resurrection of Christian Cloud at the ballot box.
We tell Christians to get out and vote.
Calling all Christians.
This weekend, millions of believers across the nation will be casting their votes.
For biblical values.
This is our moment to come together as the body of Christ.
And this is our opportunity to shape the future of our country.
And to stand firm in our beliefs.
I need you to make your voice heard.
Early voting is underway so you know what you have to do.
I need you to get out and vote.
Rally your family, call your friends.
And let's come together in unity.
Voting isn't just a right, it's our power.
It's time to stand up and save your country.
Can we count on you?
Are you with us?
Are you with us?
Are you with us?
I need you to tell every believer to get out and vote for Donald J. Trump.
    """
    # video_content = None  # 示例：无视频内容时可设为 None

    # 构建输入内容
    input_content = build_input_content(decoded_text, video_content)
    create_time = "2024-10-30 05-56"
    user_name = "Donald J. Trump"
    task_date = datetime.datetime.now().strftime("%Y年%m月%d日%H时%M分")
    task_log_file_path = os.path.join(f"task_{task_date}.log")
    logger = get_logger(__name__, f"{task_log_file_path}")

    # 调用分析助手
    research_shared = {
        "user_name": user_name, "create_time": create_time, "post": input_content, "logger": logger
    }
    context_agent_flow = context_research_flow()
    context_agent_flow.run(research_shared)

    context = research_shared.get("context", "内容未分析完成")

    # 打印结果
    print("\n===== 最终分析结果 =====\n")
    print(context)
    print("\n========================\n")
