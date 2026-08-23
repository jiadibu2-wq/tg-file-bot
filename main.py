import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 配置密钥与 API 信息
TELEGRAM_BOT_TOKEN = "你的_TELEGRAM_BOT_TOKEN"
YOUR_API_KEY = "sk-NAZIlSMeQxpLmS3IuX1vcAh7c1usKKbihB9Ktof1kNVCfGSO"
YOUR_API_URL = "{"_type":"newapi_channel_conn","key":"sk-NAZIlSMeQxpLmS3IuX1vcAh7c1usKKbihB9Ktof1kNVCfGSO","url":"https://kapibala.asia"}" # 替换为你的 API 地址

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 你好！随时将文本文件或文档发给我，我会为你处理。")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ 收到文件，正在下载并解析...")
    
    # 1. 获取手机发送的文件
    document = update.message.document
    file = await context.bot.get_file(document.file_id)
    file_path = f"./downloaded_{document.file_name}"
    await file.download_to_drive(file_path)

    # 2. 读取文件内容 (以纯文本/Markdown/代码等文件为例)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
    except Exception as e:
        await status_msg.edit_text("❌ 文件读取失败，目前仅支持文本格式文件。")
        return

    await status_msg.edit_text("🤖 正在调用 API 进行深度处理...")

    # 3. 构建请求调用你的 API
    headers = {
        "Authorization": f"Bearer {YOUR_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o", # 替换为你使用的模型名称
        "messages": [
            {"role": "system", "content": "你是一个高效的文件处理助手。请分析用户提供的文件内容，进行提炼总结并输出关键要点。"},
            {"role": "user", "content": f"以下是文件内容：\n\n{file_content}"}
        ]
    }

    try:
        response = requests.post(YOUR_API_URL, json=payload, headers=headers)
        result_text = response.json()["choices"][0]["message"]["content"]
        
        # 4. 将处理结果写入新文件回传，或者直接发送文本
        output_file_path = f"./result_{document.file_name}"
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(result_text)

        # 5. 发送处理结果给手机 Telegram
        await status_msg.edit_text("✅ 处理完成，正在为您生成结果文档：")
        await update.message.reply_document(document=open(output_file_path, "rb"), caption="这是为您整理好的处理结果。")

    except Exception as e:
        await status_msg.edit_text(f"❌ 调用 API 出错: {str(e)}")
    
    # 清理临时文件
    if os.path.exists(file_path): os.remove(file_path)
    if os.path.exists(output_file_path): os.remove(output_file_path)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.DOCUMENT, handle_document))
    
    print("Bot 已经启动，等待手机端指令...")
    app.run_polling()
