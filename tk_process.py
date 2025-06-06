import datetime
import html
import re

import chardet
import pandas as pd
import os
# 导入 agent 和 logger
from agent.main import social_assessor_assistant, extract_time_from_filename
from agent.log_config import get_logger


def build_input_content(text_content: str, tk_topic, video_content: str = None) -> str:
    # 确保 text_content 是字符串并清理
    cleaned_text = re.sub(r'https?://\S+', '', str(text_content))
    cleaned_text = html.unescape(cleaned_text.strip())

    content_parts = ["帖子文本内容：", cleaned_text]

    if tk_topic:
        # 确保话题标签是字符串
        content_parts.append("")
        content_parts.append("帖子话题标签：")
        content_parts.append(str(tk_topic).strip())

    if video_content:
        # 确保视频内容是字符串
        content_parts.append("")
        content_parts.append("帖子视听文本数据：")
        content_parts.append(str(video_content).strip())

    return "\n".join(content_parts)


# 尝试自动检测编码并读取 CSV
def read_csv_with_encoding(file_path, usecols=None):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read(10000))
        encoding = result['encoding'] or 'utf-8'

    encodings_to_try = [encoding, 'utf-8-sig', 'gbk', 'latin1', 'iso-8859-1']
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(file_path, encoding=enc, usecols=usecols, on_bad_lines='skip')
            print(f"✅ 成功使用编码 {enc} 读取文件。")
            return df
        except Exception as e:
            print(f"❌ 尝试编码 {enc} 失败: {e}")
    return None


def tk_process():
    task_date = datetime.datetime.now().strftime("%Y年%m月%d日%H时%M分")
    task_log_file_path = os.path.join(f"task_{task_date}.log")
    logger = get_logger(__name__, f"{task_log_file_path}")
    logger.info("开始处理tk社交媒体数据分析任务...")

    # 设置路径
    base_path = os.path.dirname(os.path.abspath(__file__))  # 自动获取当前项目根目录
    social_data_path = os.path.join(base_path, "social_data", "tk", "Trump quotes", "social_data.xlsx")
    video_sct_path = os.path.join(base_path, "social_data", "tk", "Trump quotes", "video_sct.csv")
    # 保存更新后的 CSV
    output_path = os.path.join(base_path, "social_data", "tk", "Trump quotes", "tk_social_data_enhanced.csv")

    def extract_video_id(input: str) -> str:
        match = re.match(r'^(\d+)', input)
        return match.group(1) if match else None

    # 读取CSV文件
    try:
        with open(social_data_path, 'rb') as f:
            # 读取 Excel 文件指定列
            social_df = pd.read_excel(
                social_data_path,
                usecols=(  # 使用字符串列名时，必须指定 header=0
                    "账号昵称", "作品ID", "作品描述",  "作品链接", "发布时间",
                    "点赞数量", "评论数量", "收藏数量", "分享数量", "播放数量"
                ),
                header=0  # 明确第一行为列头
            )
            social_df.rename(columns={
                "账号昵称": "社媒人名称",
                "作品描述": "社媒文本内容",
                "作品链接": "来源链接"
            }, inplace=True)
            social_df['社媒人名称'] = 'Donald J. Trump'

            social_df['作品ID'] = social_df['作品ID'].astype(str).apply(extract_video_id)

        with open(social_data_path, 'rb') as f:
            video_df = read_csv_with_encoding(video_sct_path, usecols=["file_name", "Contents"])

            # 再通过 rename 修改列名为中文
            video_df.rename(columns={
                "file_name": "多媒体文件名称",
                "Contents": "视频字幕或文字图片对应-文本内容"
            }, inplace=True)
        video_df['多媒体文件名称'] = video_df['多媒体文件名称'].apply(extract_video_id)

        logger.info("成功加载 social_data.csv 和 video_sct.csv。")
    except Exception as e:
        logger.error(f"读取CSV文件失败: {e}")
        return

    # 合并数据（inner join on Saved Filename = file_name）
    merged_df = pd.merge(
        social_df,
        video_df,
        left_on="作品ID",
        right_on="多媒体文件名称",
        how="inner"
    )
    # 合并完成后立即删除冗余列
    merged_df.drop(columns=["多媒体文件名称"], inplace=True)
    # 合并完成后立即删除冗余列

    # 确保 Contents 不为空
    merged_df = merged_df[merged_df["视频字幕或文字图片对应-文本内容"].notna()]
    logger.info(f"合并后有效数据共 {len(merged_df)} 行。")

    # 新增列
    merged_df['来源'] = 'TikTok'
    merged_df['主题'] = ''
    merged_df['情感倾向'] = ''
    merged_df['表达风格'] = ''
    merged_df['相关事件'] = ''
    merged_df.drop(columns=["作品ID"], inplace=True)

    # 循环处理每一行
    for index, row in merged_df.iterrows():
        user_name = row["社媒人名称"]
        tk_content = row["社媒文本内容"]

        video_content = row["视频字幕或文字图片对应-文本内容"]

        create_time = row["发布时间"]

        input_content = build_input_content(tk_content, video_content)

        logger.info(f"正在分析用户 [{user_name}] 的帖子，时间：{create_time}")

        # 调用 agent 函数

        # result = social_assessor_assistant(user_name, create_time, input_content, logger,
        #                                    social_data_path=social_data_path, columns_key="作品ID",
        #                                    columns_vlue=post_id, context="不搜索到此内容的相关背景")
        result, context = social_assessor_assistant(user_name, create_time, input_content, logger)

        try:
            # 假设返回的是 JSON 格式字符串或字典
            if isinstance(result, str):
                result_dict = eval(result)  # 如果是字符串形式的 dict
            else:
                result_dict = result

            # 写入 DataFrame
            merged_df.at[index, '主题'] = ", ".join(result_dict.get('topics', []))
            merged_df.at[index, '情感倾向'] = result_dict.get('sentiment', '')
            merged_df.at[index, '表达风格'] = result_dict.get('style', '')
            merged_df.at[index, '相关事件'] = ", ".join(result_dict.get('related_events', []))
            merged_df.at[index, '内容背景'] = context

            logger.info(f"[处理完成] 用户 [{user_name}], 结果已写入。")

            # 以追加模式写入当前行
            # 构造当前行的 DataFrame
            current_row_df = merged_df.iloc[[index]]

            write_header = False  # 后续不再写入表头
            if index == 0:
                write_header = True
            current_row_df.to_csv(
                output_path,
                mode='a',
                header=write_header,
                index=False,
                encoding="utf-8-sig"
            )

            logger.info(f"当前进度已保存至 {output_path}")

        except Exception as e:
            logger.error(f"解析结果失败: {e}, 原始结果为: {result}")
            continue

    #
    # merged_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"所有数据处理完成，结果已保存至 {output_path}")


if __name__ == "__main__":
    tk_process()
