import datetime
import html
import re

import chardet
import pandas as pd
import os
# 导入 agent 和 logger
from agent.main import social_assessor_assistant, extract_time_from_filename
from agent.log_config import get_logger

def build_input_content(text_content: str, video_content: str = None) -> str:
    cleaned_text = re.sub(r'https?://\S+', '', text_content)
    text_content = html.unescape(cleaned_text.strip())
    content_parts = ["帖子文本内容：", text_content]

    if video_content:
        content_parts.append("")  # 添加空行作为分隔
        content_parts.extend(["帖子视听文本数据：", video_content])

    return "\n".join(content_parts)
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
def twitter_process():
    task_date = datetime.datetime.now().strftime("%Y年%m月%d日%H时%M分")
    task_log_file_path = os.path.join(f"task_{task_date}.log")
    logger = get_logger(__name__, f"{task_log_file_path}")
    logger.info("开始处理TK社交媒体数据分析任务...")

    # 设置路径
    base_path = os.path.dirname(os.path.abspath(__file__))  # 自动获取当前项目根目录
    social_data_path = os.path.join(base_path, "social_data", "twitter", "relDonaldTrump", "social_data.csv")
    video_sct_path = os.path.join(base_path, "social_data", "twitter", "relDonaldTrump", "video_sct.csv")
    output_path = os.path.join(base_path, "social_data", "twitter", "relDonaldTrump", "twitter_social_data_enhanced.csv")

    import chardet

    # 读取CSV文件
    try:
        with open(social_data_path, 'rb') as f:
            social_df = pd.read_csv(social_data_path, encoding=chardet.detect(f.read(10000))['encoding'],
                                    usecols=["Display Name", "Saved Filename", "Tweet Content", 'Favorite Count',
                                             'Retweet Count', 'Reply Count', 'Tweet URL'])

            # 再通过 rename 修改列名为中文
            social_df.rename(columns={
                "Display Name": "社媒人名称",
                "Saved Filename": "多媒体文件名称",
                "Tweet Content": "社媒文本内容",
                "Favorite Count": "点赞数",
                "Retweet Count": "转发数",
                "Reply Count": "回复数",
                "Tweet URL": "来源链接"
            }, inplace=True)

        with open(social_data_path, 'rb') as f:
            video_df = read_csv_with_encoding(video_sct_path,
                                   usecols=["file_name", "Contents"])

            # 再通过 rename 修改列名为中文
            video_df.rename(columns={
                "file_name": "多媒体文件名称-2",
                "Contents": "视频字幕或文字图片对应-文本内容"
            }, inplace=True)

        logger.info("成功加载 social_data.csv 和 video_sct.csv。")
    except Exception as e:
        logger.error(f"读取CSV文件失败: {e}")
        return

    # 合并数据（inner join on Saved Filename = file_name）
    merged_df = pd.merge(
        social_df,
        video_df,
        left_on="多媒体文件名称",
        right_on="多媒体文件名称-2",
        how="inner"
    )
    # 合并完成后立即删除冗余列
    merged_df.drop(columns=["多媒体文件名称-2"], inplace=True)

    # 确保 Contents 不为空
    merged_df = merged_df[merged_df["视频字幕或文字图片对应-文本内容"].notna()]
    logger.info(f"合并后有效数据共 {len(merged_df)} 行。")

    # 新增列
    merged_df['发布时间'] = ''
    merged_df['来源'] = '推特'
    merged_df['主题'] = ''
    merged_df['情感倾向'] = ''
    merged_df['表达风格'] = ''
    merged_df['相关事件'] = ''

    def clean_tweet(text):
        # 移除 URL
        text = re.sub(r'https?://\S+', '', str(text))
        # HTML 实体转义
        text = html.unescape(text)
        # 保留中英文、数字、空格、基本标点
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?]', '', text)
        return text.strip()

    # 应用清洗逻辑到 '推文内容' 列
    merged_df['社媒文本内容'] = merged_df['社媒文本内容'].apply(clean_tweet)

    # 循环处理每一行
    for index, row in merged_df.iterrows():
        user_name = row["社媒人名称"]
        saved_file = row["多媒体文件名称"]
        tweet_content = row["社媒文本内容"]
        video_content = row["视频字幕或文字图片对应-文本内容"]

        create_time = extract_time_from_filename(saved_file)

        merged_df.at[index, '发布时间'] = create_time

        input_content = build_input_content(tweet_content, video_content)

        logger.info(f"正在分析用户 [{user_name}] 的帖子，时间：{create_time}")

        # 调用 agent 函数

        result,context = social_assessor_assistant(user_name, create_time, input_content, logger)

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
            merged_df.at[index, '背景'] = context

            logger.info(f"[处理完成] 用户 [{user_name}], 结果已写入。")
            # 以追加模式写入当前行
            # 构造当前行的 DataFrame
            current_row_df = merged_df.iloc[[index]]
            write_header = False  # 后续不再写入表头

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

    # 保存更新后的 CSV
    logger.info(f"所有数据处理完成，结果已保存至 {output_path}")


if __name__ == "__main__":
    twitter_process()
