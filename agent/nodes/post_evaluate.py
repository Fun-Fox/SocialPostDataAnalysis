import os
import re

from dotenv import load_dotenv
from pocketflow import Node
import yaml

from agent.utils.call_llm import call_llm

load_dotenv()

__all__ = ["PostEvaluate","SupervisorNode"]


class PostEvaluate(Node):
    def prep(self, shared):
        """
        从共享数据中获取贴子的评估
        """
        # todo 将背景调研的结果存储在csv中去

        return shared["post"],shared["context"], shared["logger"]

    def exec(self, inputs):

        post, context, logger = inputs
        prompt = f"""
你是一个专业的内容分析师，结合内容背景并参考分析维度，社交媒体的帖子内容进行分析
## 上下文

{context}

{post}

## 分析维度
topics：提取帖子中最能概括核心内容的关键词或话题标签，要求覆盖核心语义，数量不限

sentiment：判断帖子的整体情感倾向，取值包括：

- positive：积极、赞赏、支持
- negative：消极、不满、批评
- neutral：客观、中立陈述
- mixed：包含多种矛盾情感

style：分析帖子的语言风格，常见类型：
- formal：正式、严谨、书面化
- informal：口语化、随意、亲切
- humorous：诙谐、搞笑、趣味性强
- sarcastic：讽刺、反讽、调侃
- aggressive：攻击性、激烈、情绪化
- inspirational：激励、鼓舞、正能量

related_events：识别帖子关联的现实事件或热点话题，无则返回无热点事件。

## 返回格式

```yaml
topics: ["关键词1" ,"关键词2"]
sentiment: <整体情绪倾向> 
style: <语言风格>
related_events: ["关联事件1","关联事件2"]
```

重要！请确保：
- 使用英文双引号包裹字符串；
- 每个字段独占一行；
- 每行冒号后保留一个空格；
- 列表使用方括号 `[ ]` 包裹；
- 不要使用中文符号（如 `。`、`、`、`“”`）；
- 如果有换行文本字段，请用 `|` 表示多行字符串，并保持 4 空格缩进；
"""

        response,success = call_llm(prompt, logger )
        logger.info(f"LLM 响应: {response}")
        if "```yaml" not in response:
            logger.error("LLM 响应格式不正确，请检查你的响应格式。")
            return {"action": "finish", "reason": "LLM 响应格式不正确"}
        try:
            yaml_str = response.replace("\"", "").replace("\'", "").replace("\n", "").split("```yaml")[1].split("```")[0].strip()
            yaml_str = yaml_str.replace("。", ".").replace("，", ",").replace("：", ":").replace("“", '"').replace("”",'"')
            # 插入换行符，强制每行一个字段
            yaml_str = re.sub(r'(sentiment:|style:|related_events:)', r'\n\1', yaml_str)

        except Exception as e:
            logger.error(f"处理 LLM 响应时发生错误: {e}")
            return {"action": "finish", "reason": "LLM 响应格式不正确"}
        decision = yaml.safe_load(yaml_str)

        return decision

    def post(self, shared, prep_res, exec_res):
        """
        将最终文章存储在共享数据中
        """
        shared["post_evaluate"] = exec_res
        logger = shared["logger"]
        logger.info(f"===内容评估完成===")
        return "evaluate"


# 监督节点
class SupervisorNode(Node):
    def prep(self, shared):
        """获取当前回答以进行评估。"""
        return shared["post_evaluate"], shared["logger"]

    def exec(self, inputs):
        """检查回答是否有效或无意义。"""
        post_evaluate, logger = inputs
        logger.info(f"监督员正在检查回答质量...")

        # 检查无意义回答的明显标记
        nonsense_markers = [
            "coffee break",
            "purple unicorns",
            "made up",
            "42",
            "Who knows?"
        ]

        # 检查回答是否包含任何无意义标记
        is_nonsense = any(marker in post_evaluate for marker in nonsense_markers)

        if is_nonsense:
            return {"valid": False, "reason": "回答似乎无意义或无帮助"}
        else:
            return {"valid": True, "reason": "回答似乎是合法的"}

    def post(self, shared, prep_res, exec_res):
        logger = shared["logger"]
        """决定是否接受回答或重新启动流程。"""
        if exec_res["valid"]:
            logger.info(f"监督员批准了回答: {exec_res['reason']}")
            return "approved"
        else:
            logger.info(f"监督员拒绝了回答: {exec_res['reason']}")
            # 清理错误的回答
            shared["post_evaluate"] = None
            # 添加关于被拒绝回答的注释
            context = shared.get("post_evaluate", "")
            shared["post"] = context + "\n\n注意: 之前的回答尝试被监督员拒绝了。"

            return "retry"



