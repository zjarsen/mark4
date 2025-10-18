import asyncio
import os
import time
import aiohttp
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Bot token
BOT_TOKEN = "8119215433:AAGWetPqiUcwFPe7rbIa7DIa5LsRbM0HuQQ"

# ComfyUI server settings
COMFYUI_SERVER = "http://20.196.153.126:8188"
COMFYUI_UPLOAD_URL = f"{COMFYUI_SERVER}/upload/image"

# Storage directories
USER_UPLOADS_DIR = os.path.expanduser("~/mark4/user_uploads")
COMFYUI_RETRIEVE_DIR = os.path.expanduser("~/mark4/comfyui_retrieve")

# User state tracking
user_states = {}
user_queue_messages = {}
cleanup_tasks = {}

os.makedirs(USER_UPLOADS_DIR, exist_ok=True)
os.makedirs(COMFYUI_RETRIEVE_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and show menu."""
    user_id = update.effective_user.id

    # Check if this is the first time user connects
    if user_id not in user_states:
        await update.message.reply_text('欢迎光临免费版脱衣bot!\n简单的使用说明：仅需选择“图片脱衣”，上传一张尽量正脸的照片，可以半身可以全身，AI就会直接帮你把衣服脱掉～')
        user_states[user_id] = {'first_contact': True}

    # Show menu with three options
    keyboard = [
        [KeyboardButton("1. 图片脱衣")],
        [KeyboardButton("2. 图片转视频脱衣（暂未开放）")],
        [KeyboardButton("3. 查看队列")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    await update.message.reply_text(
        '请选择功能：',
        reply_markup=reply_markup
    )

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu option selection."""
    user_id = update.effective_user.id
    text = update.message.text

    if text == "1. 图片脱衣":
        # Option 1: Image processing
        user_states[user_id] = {'state': 'waiting_for_image', 'retry_count': 0}
        await update.message.reply_text("请现在向我发送图片")

    elif text == "2. 图片转视频脱衣":
        # Option 2: Not implemented yet
        await update.message.reply_text("此功能仍在开发中")

    elif text == "3. 查看队列":
        # Option 3: Check queue status
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{COMFYUI_SERVER}/queue") as resp:
                    if resp.status == 200:
                        queue_data = await resp.json()
                        queue_pending = queue_data.get('queue_pending', [])
                        queue_running = queue_data.get('queue_running', [])
                        total_queue = len(queue_pending) + len(queue_running)
                        await update.message.reply_text(f"当前队列总人数为：{total_queue}")
                    else:
                        await update.message.reply_text("无法获取队列信息，请稍后再试")
            except Exception as e:
                await update.message.reply_text("无法获取队列信息，请稍后再试")

    else:
        # Echo other messages
        await update.message.reply_text(update.message.text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads from users."""
    user_id = update.effective_user.id

    # Check if user is in the right state
    if user_id not in user_states or user_states[user_id].get('state') != 'waiting_for_image':
        await update.message.reply_text("请先选择 '1. 图片脱衣' 功能")
        return

    # Check if user already has an image processing
    if user_states[user_id].get('state') == 'processing':
        await update.message.reply_text("您上传的图片仍在队列中，请耐心等待")
        return

    # Reset retry count on successful photo upload
    user_states[user_id]['retry_count'] = 0

    # Get the photo
    photo = update.message.photo[-1]  # Get highest resolution
    file = await context.bot.get_file(photo.file_id)

    # Create filename with user_id and timestamp
    timestamp = int(time.time())
    filename = f"{user_id}_{timestamp}.jpg"
    local_path = os.path.join(USER_UPLOADS_DIR, filename)

    # Download the photo
    await file.download_to_drive(local_path)

    # Upload to ComfyUI and queue
    try:
        await upload_and_queue_image(update, context, local_path, filename, user_id)
    except Exception as e:
        await update.message.reply_text(f"上传失败: {str(e)}")
        user_states[user_id] = {}

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads (images sent as files)."""
    user_id = update.effective_user.id

    # Check if user is in the right state
    if user_id not in user_states or user_states[user_id].get('state') != 'waiting_for_image':
        return

    # Check if user already has an image processing
    if user_states[user_id].get('state') == 'processing':
        await update.message.reply_text("您上传的图片仍在队列中，请耐心等待")
        return

    document = update.message.document
    file_name = document.file_name.lower()
    allowed_formats = ['png', 'jpg', 'jpeg', 'webp']

    # Check if file extension is valid
    file_extension = file_name.split('.')[-1] if '.' in file_name else ''

    if file_extension not in allowed_formats:
        await handle_invalid_format(update, context, user_id)
        return

    # Valid format - reset retry count and process
    user_states[user_id]['retry_count'] = 0

    # Get the file
    file = await context.bot.get_file(document.file_id)

    # Create filename with user_id and timestamp
    timestamp = int(time.time())
    filename = f"{user_id}_{timestamp}.{file_extension}"
    local_path = os.path.join(USER_UPLOADS_DIR, filename)

    # Download the file
    await file.download_to_drive(local_path)

    # Upload to ComfyUI and queue
    try:
        await upload_and_queue_image(update, context, local_path, filename, user_id)
    except Exception as e:
        await update.message.reply_text(f"上传失败: {str(e)}")
        user_states[user_id] = {}

async def handle_invalid_format(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Handle invalid file format uploads."""
    user_states[user_id]['retry_count'] = user_states[user_id].get('retry_count', 0) + 1

    if user_states[user_id]['retry_count'] >= 3:
        # Delete previous messages except welcome
        await update.message.reply_text("您已尝试3次，请重新开始。")
        user_states[user_id] = {}

        # Show menu again
        keyboard = [
            [KeyboardButton("1. 图片脱衣")],
            [KeyboardButton("2. 图片转视频脱衣")],
            [KeyboardButton("3. 查看队列")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text('请选择功能：', reply_markup=reply_markup)
    else:
        await update.message.reply_text('您发送的文件格式有误，请发送以下图片格式之一："png", "jpg", "jpeg", "webp"')

async def handle_text_during_image_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages when user should be sending an image."""
    user_id = update.effective_user.id
    text = update.message.text

    # Exclude menu options from being treated as invalid
    menu_options = ["1. 图片脱衣", "2. 图片转视频脱衣", "3. 查看队列"]
    if text in menu_options:
        return

    # Check if user is in waiting for image state
    if user_id in user_states and user_states[user_id].get('state') == 'waiting_for_image':
        await handle_invalid_format(update, context, user_id)

async def upload_and_queue_image(update, context, local_path, filename, user_id):
    """Upload image to ComfyUI server and start processing."""

    async with aiohttp.ClientSession() as session:
        # Upload the image
        with open(local_path, 'rb') as f:
            form = aiohttp.FormData()
            form.add_field('image', f, filename=filename, content_type='image/jpeg')

            async with session.post(COMFYUI_UPLOAD_URL, data=form) as resp:
                if resp.status != 200:
                    raise Exception(f"Upload failed with status {resp.status}")
                upload_result = await resp.json()

        # Queue the prompt (you'll need to customize this with your actual workflow)
        workflow = create_comfyui_workflow(filename)
        prompt_data = {"prompt": workflow}

        async with session.post(f"{COMFYUI_SERVER}/prompt", json=prompt_data) as resp:
            if resp.status != 200:
                raise Exception(f"Queue failed with status {resp.status}")
            queue_result = await resp.json()
            prompt_id = queue_result.get('prompt_id')

        # Store prompt_id for tracking
        user_states[user_id] = {
            'state': 'processing',
            'prompt_id': prompt_id,
            'filename': filename
        }

        # Get initial queue position and send message
        queue_position, total_queue = await get_queue_position(session, prompt_id)

        # Create inline button for refresh
        keyboard = [[InlineKeyboardButton("刷新队列", callback_data=f"refresh_{prompt_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        queue_msg = await update.message.reply_text(
            f"已经进入队列，您现在的排队为第{queue_position}位。队列总人数为：{total_queue}\n\n点击 '刷新队列' 看最新排位",
            reply_markup=reply_markup
        )

        # Store message for later updates/deletion
        user_queue_messages[user_id] = queue_msg

        # Start monitoring the queue
        asyncio.create_task(monitor_processing(context, user_id, prompt_id, filename))

async def get_queue_position(session, prompt_id):
    """Get the position of a prompt in the queue and total queue size."""
    try:
        async with session.get(f"{COMFYUI_SERVER}/queue") as resp:
            if resp.status == 200:
                queue_data = await resp.json()
                queue_pending = queue_data.get('queue_pending', [])
                queue_running = queue_data.get('queue_running', [])

                # Calculate total queue size
                total_queue = len(queue_pending) + len(queue_running)

                # Find position in queue
                for idx, item in enumerate(queue_pending):
                    if item[1] == prompt_id:
                        return idx + 1, total_queue

                # If not in pending, might be running
                if queue_running and queue_running[0][1] == prompt_id:
                    return 1, total_queue

                return 0, total_queue  # Completed or not found
    except:
        return -1, -1  # Error

async def refresh_queue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle refresh queue button clicks."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    prompt_id = query.data.replace("refresh_", "")

    # Get current queue position
    async with aiohttp.ClientSession() as session:
        queue_position, total_queue = await get_queue_position(session, prompt_id)

    if queue_position > 0:
        keyboard = [[InlineKeyboardButton("刷新队列", callback_data=f"refresh_{prompt_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"已经进入队列，您现在的排队为第{queue_position}位。队列总人数为：{total_queue}\n\n点击 '刷新队列' 看最新排位",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text("处理中...")

async def monitor_processing(context, user_id, prompt_id, filename):
    """Monitor ComfyUI processing and retrieve completed image."""

    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds

            try:
                # Check history to see if completed
                async with session.get(f"{COMFYUI_SERVER}/history/{prompt_id}") as resp:
                    if resp.status == 200:
                        history = await resp.json()

                        if prompt_id in history:
                            # Processing completed
                            outputs = history[prompt_id].get('outputs', {})

                            # Find the output image from node "27"
                            output_image = None
                            if "27" in outputs and 'images' in outputs["27"]:
                                output_image = outputs["27"]['images'][0]

                            if output_image:
                                # Download the processed image
                                image_filename = output_image['filename']
                                image_url = f"{COMFYUI_SERVER}/view?filename={image_filename}"

                                # Download to retrieve folder
                                base_name = os.path.splitext(filename)[0]
                                output_path = os.path.join(COMFYUI_RETRIEVE_DIR, f"{base_name}_complete.jpg")

                                async with session.get(image_url) as img_resp:
                                    if img_resp.status == 200:
                                        with open(output_path, 'wb') as f:
                                            f.write(await img_resp.read())

                                # Send image first, then completion message
                                msg = await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=open(output_path, 'rb')
                                )

                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text="处理完成！请在5分钟内尽快储存"
                                )

                                # Delete queue message
                                if user_id in user_queue_messages:
                                    try:
                                        await user_queue_messages[user_id].delete()
                                        del user_queue_messages[user_id]
                                    except:
                                        pass

                                # Schedule cleanup after 5 minutes
                                cleanup_tasks[user_id] = asyncio.create_task(
                                    cleanup_after_timeout(context, user_id, filename, output_path, msg.message_id)
                                )

                                # Reset user state
                                user_states[user_id] = {}
                                break

            except Exception as e:
                print(f"Error monitoring: {e}")
                await asyncio.sleep(5)

async def cleanup_after_timeout(context, user_id, original_filename, output_path, message_id):
    """Delete images and message after 5 minutes."""
    await asyncio.sleep(300)  # 5 minutes

    # # Delete user upload
    # original_path = os.path.join(USER_UPLOADS_DIR, original_filename)
    # if os.path.exists(original_path):
    #     os.remove(original_path)

    # # Delete retrieved image
    # if os.path.exists(output_path):
    #     os.remove(output_path)

    # # Delete the image message from chat
    # try:
    #     await context.bot.delete_message(chat_id=user_id, message_id=message_id)
    # except:
    #     pass

    # Clean up task reference
    if user_id in cleanup_tasks:
        del cleanup_tasks[user_id]

def create_comfyui_workflow(image_filename):
    """Load ComfyUI workflow from JSON file and update with the uploaded image filename."""
    workflow_path = os.path.expanduser("~/mark4/workflows/qwen_image_edit_final.json")

    with open(workflow_path, 'r') as f:
        workflow = json.load(f)

    # Update the LoadImage node (node "7") with the uploaded image filename
    if "7" in workflow:
        workflow["7"]["inputs"]["image"] = image_filename

    return workflow

def main():
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex(r"^(1\. 图片脱衣|2\. 图片转视频脱衣|3\. 查看队列)$"), handle_menu_selection))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(refresh_queue_callback, pattern="^refresh_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_during_image_wait))

    print("Bot is starting...")
    print("Bot username: declothing_free1_bot")
    print("You can start chatting with the bot now!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
