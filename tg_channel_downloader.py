# !/usr/bin/env python3
import asyncio
import asyncio.subprocess
import difflib
import logging
import os
import re
import sys
import time

import socks
from telethon import TelegramClient, events, errors
from telethon.errors import FloodWaitError
from telethon.tl.types import InputMessagesFilterPhotos, \
    InputMessagesFilterDocument, InputMessagesFilterVideo, InputMessagesFilterMusic

from tg_sqlite import Sqlite3Helper

sysname = sys.platform
is_test = False
if 'linux' not in sysname:
    is_test = True

tele_mobile = '139'
proxy_use = True

db_file = 'linesDB.db'
lineDB = Sqlite3Helper(db_file)
lineDB.create_table('line2down',
                    'ID INTEGER PRIMARY KEY AUTOINCREMENT,CHANNEL_ID INTEGER NOT NULL ,CHANNEL_USERNAME TEXT NOT NULL ,FILE_NAME TEXT NOT NULL ,OFFSITE_ID INTEGER NOT NULL ,STATUS INTEGER')
# STATUS : 0 正在下载 1 下载完成 2 不需下载


if tele_mobile == '139':
    api_id = 27545157  # your telegram api id
    api_hash = '8b71c214b961905539c966b866bb4499'  # test api hash
    bot_token = '5598238561:AAFKnE3bxT5IgknfVyVCsdfxxkW1CJDw-nA'  # your bot_token
    admin_id = 742779974  # your chat id
    socks_port = 52608
elif tele_mobile == '147':
    api_id = 16852383  # your telegram api id
    api_hash = '88f647d70da0b07ba9fcf69365f7761c'  # your telegram api hash
    bot_token = '1281281363:AAF5CcmygZtZT0Xbnd1xRRNN7CiZgARA76c'  # your bot_token
    admin_id = 973926105  # your chat id
    socks_port = 52908
elif tele_mobile == '153':
    api_id = 21971696  # your telegram api id
    api_hash = '6f6d1ab0323a9e23ad5a7da6267e7f45'  # your telegram api hash
    bot_token = '6147440310:AAHDmwkypScL5qYaX_qI-bEeGMr1gOt5tGg'  # your bot_token
    admin_id = 973926105  # your chat id
    socks_port = 52608

if is_test:
    # test 环境
    save_path = '/Users/wuyun/Downloads/Other/Telegram'  # file save path
    socks_port = 62808
else:
    save_path = '/mnt/onedrive/moux-docu/telegram'  # file save path

upload_file_set = False  # set upload file to google drive
drive_name = 'moux-docu'  # rclone drive name
max_num = 3  # 同时下载数量

# filter file name/文件名过滤
# filter_list/文件名过滤
filter_list = ['你好，欢迎加入 Quantumu', '\n']
# filter chat id /过滤某些频道不下载
blacklist = [1388464914]
filter_file_name = ['png', 'gif']

min_video_length = 600  # 下载视频要求的最短时间
# ***********************************************************************************#

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)
queue = asyncio.Queue(maxsize=20)


# 文件夹/文件名称处理
def validateTitle(title):
    r_str = r"[\/\\\:\*\?\"\<\>#\.\|\n\s]+"  # '/ \ : * ? " < > |'
    new_title = re.sub(r_str, "_", title)  # 替换为下划线
    pattern = re.compile(r'\(http.+\)|\[.+\]')
    new_title2 = re.sub(pattern, "", new_title)
    new_title3 = re.sub('__', '_', new_title2)
    return new_title3


def has_japanese_kana(string):
    # 匹配平假名或片假名的正则表达式
    pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF]')
    # 如果匹配成功则返回true，否则返回false
    return bool(pattern.search(string))


# 文件类型标准名转换
def mimeTypeTrans(extname):
    mimename = None
    if extname == 'mp3':
        mimename = ['audio/mpeg', 'audio/x-ms-wma', 'audio/aac', 'audio/ogg', 'audio/x-wavis', 'audio/mp4']
    elif extname == 'mp4':
        mimename = ['video/mpeg', 'video/mp4', 'audio/x-ms-wmv']
    elif extname == 'txt':
        mimename = ['text/plain']
    elif extname == 'jpg':
        mimename = ['image/jpeg']
    elif extname == 'zip':
        mimename = ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed']
    return mimename


# 获取相册标题
async def get_group_caption(message):
    group_caption = ""
    entity = await client.get_entity(message.to_id)
    async for msg in client.iter_messages(entity=entity, reverse=True, offset_id=message.id - 9, limit=10):
        if msg.grouped_id == message.grouped_id:
            if msg.text != "":
                group_caption = msg.text
                return group_caption
    return group_caption


# 获取本地时间
def get_local_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

# 判断相似率
def get_equal_rate(str1, str2):
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()


# 返回文件大小
def bytes_to_string(byte_count):
    suffix_index = 0
    while byte_count >= 1024:
        byte_count /= 1024
        suffix_index += 1

    return '{:.2f}{}'.format(
        byte_count, [' bytes', 'KB', 'MB', 'GB', 'TB'][suffix_index]
    )


# 用于跳过特定格式文件
def skip(file_name):
    for filter_file in filter_file_name:
        if file_name.endswith(filter_file):
            print('skip .' + filter_file + ' file ' + file_name)
            return True


# 添加任务到队列
async def add2lines(orders):
    chat_id = orders['chat_id']
    if chat_id == '':
        # await bot.send_message(admin_id, '参数错误，请按照参考格式输入:\n\n'
        #                                  '<i>https://t.me/namestring </i>\n\n'
        #                                  '<i>https://t.me/namestring/100 </i>\n\n'
        #                                  '<i>https://t.me/namestring 0 </i>\n\n'
        #                                  '<i>https://t.me/namestring 0 100 </i>\n\n'
        #                                  '<i>https://t.me/namestring 0 100 video </i>\n\n'
        #                                  '<i>https://t.me/namestring 0 100 video 10 </i>\n\n'
        #                                  'Tips:最多5参数：1频道 2起始id 3下载个数 4类型 5媒体最小分钟数',
        #                        parse_mode='HTML')
        print('参数错误，请按照参考格式输入')
        return

    offset_id = orders['offset_id']
    count_number = orders['count_number']
    file_type = orders['file_type']
    media_length = orders['media_length']

    entity = await client.get_entity(chat_id)
    chat_title = entity.title
    channel_id = entity.id
    if channel_id:
        # print(f'{get_local_time()}: 开始下载[CHAT: {chat_title}]({entity.id}) - {offset_id}')
        last_msg_id = 0
        msg_count = 0

        if file_type == 'all':
            messages = client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=count_number)
        elif file_type == 'video':
            messages = client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=count_number,
                                            filter=InputMessagesFilterVideo)
        elif file_type == 'docu':
            messages = client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=count_number,
                                            filter=InputMessagesFilterDocument)
        elif file_type == 'music':
            messages = client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=count_number,
                                            filter=InputMessagesFilterMusic)
        elif file_type == 'photo':
            messages = client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=count_number,
                                            filter=InputMessagesFilterPhotos)
        else:
            if file_type.startswith('s_'):
                file_type_str = file_type.split('_')
                file_type_keyword = file_type_str[1]
                file_type = file_type_str[2]
                messages = client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=count_number,
                                                search=file_type_keyword)
            else:
                messages = client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=count_number)

        async for message in messages:
            tips = f'[{msg_count}][{entity.username}][{chat_title}][{message.id}]'
            if message.media:
                # 如果是一组媒体
                # caption = await get_group_caption(message) if (
                #        message.grouped_id and message.text == "") else message.text
                # 过滤文件名称中的广告等词语
                caption = ''
                # if len(filter_list) and caption != "":
                #    for filter_keyword in filter_list:
                #        caption = caption.replace(filter_keyword, "")
                # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
                # caption = "" if caption == "" else f'{validateTitle(caption)} - '[
                #                                   :50]
                file_name = ''
                file_duration = 0
                # file_h = 0
                # file_w = 0

                # 判断是否下载完成过
                dbstr_sel_downed = f'CHANNEL_ID = {channel_id} and OFFSITE_ID = {message.id} and STATUS = 1'
                dbstr_result_downed = lineDB.select('line2down', 'ID', dbstr_sel_downed)
                if dbstr_result_downed:
                    print(
                        f'{tips}{file_name}已完成下载, passed  不进入下载队列。当前排队:{queue.qsize()}')
                    continue

                # 如果是文件
                if message.document:
                    if file_type not in ['all', 'photo', 'video', 'docu', 'music']:
                        media_type_name = mimeTypeTrans(file_type)
                        if message.media.document.mime_type not in media_type_name:
                            print(
                                f'{tips}不是要下载类型,不进入下载队列。当前排队:{queue.qsize()}')
                            continue
                    if message.media.document.mime_type == "image/webp":
                        continue
                    if message.media.document.mime_type == "application/x-tgsticker":
                        continue
                    for i in message.document.attributes:
                        try:
                            file_name = i.file_name
                        except:
                            continue
                    if file_type == 'video' or file_type == 'music' or message.media.document.mime_type in mimeTypeTrans(
                            'mp4') or message.media.document.mime_type in mimeTypeTrans('mp3'):
                        for i in message.document.attributes:
                            try:
                                file_duration = i.duration
                                # file_h = i.h
                                # file_w = i.w
                            except:
                                continue
                    else:
                        file_duration = -1

                    file_ext = file_name.split(".")[-1]
                    file_name_l = validateTitle(re.sub('.' + file_ext, '', file_name))

                    if file_duration > 0 and file_duration < media_length:
                        print(
                            f'{tips}{file_name}时长{file_duration}秒 小于{media_length},不进入下载队列。当前排队:{queue.qsize()}')
                        continue

                    if file_name == '':
                        file_name = f'[{message.id}].{message.document.mime_type.split("/")[-1]}'
                    else:
                        # 如果文件名中已经包含了标题，则过滤标题
                        # if get_equal_rate(caption, file_name) > 0.6:
                        #    caption = ""
                        # if caption != "":
                        #    file_name = f'[{message.id}]{file_name_l}[{validateTitle(caption)}].{file_ext}'
                        # else:
                        #    file_name = f'[{message.id}]{file_name_l}.{file_ext}'
                        file_name = f'[{message.id}]{file_name_l}.{file_ext}'
                elif message.photo:
                    file_ext = message.file.ext.lstrip('.')
                    if file_type != 'all':
                        if file_type != 'photo' and file_type != file_ext:
                            print(
                                f'{tips}{file_name} picture is not {file_type}, 不进入下载队列。当前排队:{queue.qsize()}')
                            continue
                        else:
                            if caption != "":
                                file_name = f'[{message.id}][{message.photo.id}]{file_name}[{validateTitle(caption)}].{file_ext}'
                            else:
                                file_name = f'[{message.id}][{message.photo.id}]{file_name}.{file_ext}'
                    else:
                        if caption != "":
                            file_name = f'[{message.id}][{message.photo.id}]{file_name}[{validateTitle(caption)}].{file_ext}'
                        else:
                            file_name = f'[{message.id}][{message.photo.id}]{file_name}.{file_ext}'
                else:
                    continue
                # 判断音频文件是否日文 是的话跳过下载
                if file_type == 'music':
                    if has_japanese_kana(file_name):
                        print(f'{tips}{file_name} 日文音频,不进入下载队列。当前排队:{queue.qsize()}')
                        continue

                # 判断文件是否在本地存在，如果存在且大小一致，则不进入下载队列，如果大小不一致，文件名修改加入id后缀
                dirname = f'[{channel_id}]{entity.username}'
                datetime_dir_name = message.date.strftime("%Y-%m")
                file_save_path = os.path.join(save_path, dirname, datetime_dir_name)
                # file_save_path = os.path.join(save_path, dirname)
                if os.path.exists(file_save_path):
                    if file_name in os.listdir(file_save_path):
                        exist_file_size = os.path.getsize(os.path.join(file_save_path, file_name))
                        if exist_file_size != 0:
                            new_file_size = message.file.size
                            if exist_file_size == new_file_size:
                                print(
                                    f'{tips}{file_name}文件已存在且大小一致,不进入下载队列。当前排队:{queue.qsize()}')
                                # 文件存在 更新或新建记录该信息
                                dbstr_sel_downed = f'CHANNEL_ID = {channel_id} and OFFSITE_ID = {message.id}'
                                dbstr_result_downed = lineDB.select('line2down', 'ID', dbstr_sel_downed)
                                if dbstr_result_downed:
                                    dbstr_update = f'CHANNEL_ID = {channel_id} and OFFSITE_ID = {message.id}'
                                    lineDB.update('line2down', 'status=1', dbstr_update)
                                else:
                                    dbstr_ins = f'{channel_id},\"{entity.username}\",\"{file_name}\" ,{message.id},1'
                                    lineDB.insert('line2down',
                                                  'CHANNEL_ID, CHANNEL_USERNAME, FILE_NAME, OFFSITE_ID, STATUS',
                                                  dbstr_ins)
                                continue
                            else:
                                if caption != "":
                                    file_name = f'{file_name}[{validateTitle(caption)}]'
                                else:
                                    file_name = f'{file_name}'

                print(f'{tips}{file_name}进入下载队列。当前排队:{queue.qsize()}')
                await queue.put((message, chat_title, entity, file_name, channel_id))
                msg_count = msg_count + 1
                dbstr_sel = f'CHANNEL_ID = {channel_id} and OFFSITE_ID = {message.id}'
                dbstr_result = lineDB.select('line2down', 'ID', dbstr_sel)
                if not dbstr_result:
                    dbstr_ins = f'{channel_id},\"{entity.username}\",\"{file_name}\" ,{message.id},0'
                    lineDB.insert('line2down', 'CHANNEL_ID, CHANNEL_USERNAME, FILE_NAME, OFFSITE_ID, STATUS', dbstr_ins)

                    # dbstr_result111 = lineDB.select('line2down', 'CHANNEL_USERNAME,OFFSITE_ID')

                last_msg_id = message.id
        # await bot.send_message(admin_id, f'{chat_title} all message added to task queue, last message is {str(last_msg_id)}')


# 继续之前没完成的下载
async def continue_down():
    continue_down_list = lineDB.select('line2down', 'CHANNEL_USERNAME, OFFSITE_ID, FILE_NAME', 'STATUS = 0')
    for linkdata in continue_down_list:
        # link_url = 'https://t.me/' + linkdata[0] + '/' + str(linkdata[1])
        chat_id = 'https://t.me/' + linkdata[0]
        offset_id = linkdata[1] - 1
        file_name = linkdata[2]
        entity = await client.get_entity(chat_id)
        # message = await client.get_messages(entity, ids=offset_id)
        channel_id = entity.id
        chat_title = entity.title
        try:
            # your code here
            async for new_message in client.iter_messages(entity=entity, offset_id=offset_id, reverse=True,
                                                          limit=1):
                await queue.put((new_message, chat_title, entity, file_name, channel_id))
                print(
                    f'[{entity.username}][{chat_title}][{offset_id}]{file_name} 进入下载队列。当前排队:{queue.qsize()}')
        except FloodWaitError as e:
            print('Flood wait error:', e.seconds)
        # except errors as e:
        #    print('error:', e.seconds)

    return True


# 标准化处理传入的命令
def trans_order(message):
    chat_id = 0
    offset_id = 0
    count_number = 1
    file_type = 'all'
    media_length = min_video_length
    order_is_right = False
    try:
        # if message.file.mime_type:
        #     try:
        #         file_save_path = os.path.join(save_path, 'single')
        #         if message.file.name.split(".")[0] == message.file.title:
        #             file_name = message.file.name
        #         else:
        #             file_name = f'{message.file.name.split(".")[0]}[{message.file.title}]{message.file.ext}'
        #         message.download_media(
        #             file=f'{os.path.join(file_save_path, file_name)}')
        #     except Exception as e:
        #         print(f"{get_local_time()} - {file_name} {e}")
        #     return
        if message.forward:
            chat_id = 'https://t.me/' + message.forward.chat.username
            offset_id = message.forward.channel_post - 1
            count_number = 1
            file_type = 'all'
            media_length = min_video_length
            orders = {'chat_id': chat_id, 'offset_id': offset_id, 'count_number': count_number, 'file_type': file_type,
                      'media_length': media_length}
            return orders
        texts = message.text
        texts = re.sub('\\s+', ' ', texts)
        text = texts.split(' ')
        if text[0].startswith('https://t.me/'):
            if len(text) == 1:
                chat_url = text[0].replace('?single', '').replace('https://t.me/', '').split('/')
                if len(chat_url) == 1:
                    chat_id = 'https://t.me/' + chat_url[0]
                    offset_id = 0
                    count_number = None
                elif len(chat_url) == 2:
                    chat_id = 'https://t.me/' + chat_url[0]
                    offset_id = int(chat_url[1]) - 1
                    count_number = 1
                file_type = 'all'
                media_length = min_video_length
            elif len(text) == 2:
                chat_id = text[0]
                offset_id = int(text[1])
                count_number = None
                file_type = 'all'
                media_length = min_video_length
            elif len(text) == 3:
                chat_id = text[0]
                offset_id = int(text[1])
                if text[2] == 'all':
                    count_number = None
                else:
                    count_number = int(text[2])
                file_type = 'all'
                media_length = min_video_length
            elif len(text) == 4:
                chat_id = text[0]
                offset_id = int(text[1])
                if text[2] == 'all':
                    count_number = None
                else:
                    count_number = int(text[2])
                file_type = text[3]
                media_length = min_video_length
            elif len(text) == 5:
                chat_id = text[0]
                offset_id = int(text[1])
                if text[2] == 'all':
                    count_number = None
                else:
                    count_number = int(text[2])
                file_type = text[3]
                media_length = int(text[4]) * 60
            order_is_right = True
        else:
            order_is_right = False
    except:
        return False
    if order_is_right:
        orders = {'chat_id': chat_id, 'offset_id': offset_id, 'count_number': count_number, 'file_type': file_type,
                  'media_length': media_length}
        return orders
    else:
        return False


async def worker(name):
    while True:
        # 将queue队列中的信息分别提取
        queue_item = await queue.get()
        message = queue_item[0]
        chat_title = queue_item[1]
        entity = queue_item[2]
        file_name = queue_item[3]
        channel_id = queue_item[4]
        # file_index = message.id

        # 此处对原代码(以下注释)进行优化，使其不会因过滤文件太多而停止运行
        if skip(file_name):
            continue
        # for filter_file in filter_file_name:
        #     if file_name.endswith(filter_file):
        #         print('find')
        #         return
        dirname = f'[{channel_id}]{entity.username}'
        # file_save_path = os.path.join(save_path, dirname)

        datetime_dir_name = message.date.strftime("%Y-%m")
        file_save_path = os.path.join(save_path, dirname, datetime_dir_name)

        dirname_old = f'[{channel_id}]'
        # file_save_path_old = os.path.join(save_path, dirname_old)
        file_save_path_old = os.path.join(save_path, dirname_old, datetime_dir_name)

        # 判断文件夹否在本地存在，如果存在，则分情况处理
        if not os.path.exists(file_save_path):
            if os.path.exists(file_save_path_old):
                os.rename(file_save_path_old, file_save_path)
            else:
                os.makedirs(file_save_path)

        # 判断文件是否在本地存在，如果存在，则分情况处理
        if file_name in os.listdir(file_save_path):
            new_file_size = message.file.size
            exist_file_size = os.path.getsize(os.path.join(file_save_path, file_name))
            if exist_file_size == 0:
                os.remove(os.path.join(file_save_path, file_name))
            elif exist_file_size == new_file_size:
                print(
                    f'[CHAT: [{channel_id}]{chat_title}]ID-{message.id}:{file_name} 文件已存在且大小一致,不进入下载队列。当前排队:{queue.qsize()}')
                # 文件存在 更新或新建记录该信息
                dbstr_sel_downed = f'CHANNEL_ID = {channel_id} and OFFSITE_ID = {message.id}'
                dbstr_result_downed = lineDB.select('line2down', 'ID', dbstr_sel_downed)
                if dbstr_result_downed:
                    dbstr_update = f'CHANNEL_ID = {channel_id} and OFFSITE_ID = {message.id}'
                    lineDB.update('line2down', 'status=1', dbstr_update)
                else:
                    dbstr_ins = f'{channel_id},\"{entity.username}\",\"{file_name}\" ,{message.id},1'
                    lineDB.insert('line2down',
                                  'CHANNEL_ID, CHANNEL_USERNAME, FILE_NAME, OFFSITE_ID, STATUS',
                                  dbstr_ins)
                continue
            elif exist_file_size < new_file_size:
                # file_name = f"{file_name}[{message.id}]"
                os.remove(os.path.join(file_save_path, file_name))

        # print(f"{get_local_time()} 开始下载： {chat_title} - {file_save_path} / {file_name} ")

        # 核心部分
        try:
            loop = asyncio.get_event_loop()

            def callback(current, total):
                if current >= total:
                    print(
                        f"\033[1;35m{get_local_time()}: [CHAT:  [{channel_id}]{chat_title}]ID-{message.id}:{file_name}完成下载\033[0m[当前排队:{queue.qsize()}]")
                    dbstr_update = f'CHANNEL_ID = {channel_id} and OFFSITE_ID = {message.id}'
                    lineDB.update('line2down', 'status=1', dbstr_update)

                    # bot.send_message(admin_id, f"{chat_title} - {file_name} downloaded")

            # 增加磁盘剩余空间检查 防止无空间供存储
            # 获取/目录的磁盘信息
            info = os.statvfs(file_save_path)
            free_size = info.f_bsize * info.f_bavail
            # print(f'可用磁盘空间:{free_size}MB')
            # 小于10倍则暂停下载
            if message:
                while free_size <= message.file.size * 10:
                    free_size = info.f_bsize * info.f_bavail
                    print(f"\033[1;35m{get_local_time()}磁盘空间不足，等待1分钟")
                    time.sleep(60)

            task = loop.create_task(client.download_media(
                message, os.path.join(file_save_path, file_name), progress_callback=callback))
            await asyncio.wait_for(task, timeout=3600)
            # 上传文件到网盘
            # if upload_file_set:
            #     proc = await asyncio.create_subprocess_exec('rclone',
            #                                                 'move',
            #                                                 os.path.join(
            #                                                     file_save_path, file_name),
            #                                                 f"{drive_name}:{{{drive_id}}}/{dirname}",
            #                                                 '--ignore-existing',
            #                                                 stdout=asyncio.subprocess.DEVNULL)
            #     await proc.wait()
            #     if proc.returncode == 0:
            #         print(f"{get_local_time()} - {file_name} 下载并上传完成")
        # 核心部分

        except (errors.FileReferenceExpiredError, asyncio.TimeoutError):
            print(
                f'{get_local_time()}: [CHAT: [{channel_id}]{chat_title}]ID-{message.id}:{file_name} 出现异常，重新尝试下载！')
            async for new_message in client.iter_messages(entity=entity, offset_id=message.id - 1, reverse=True,
                                                          limit=1):
                await queue.put((new_message, chat_title, entity, file_name, channel_id))
        except Exception as e:
            print(f"{get_local_time()} - {file_name} {e}")
            # await bot.send_message(admin_id, f'Error!\n\n{e}\n\n{file_name}')
        finally:
            # 确保任务正常结束
            queue.task_done()
            # # 无论是否上传成功都删除文件。
            # if upload_file_set:
            #     try:
            #         os.remove(os.path.join(file_save_path, file_name))
            #     except:
            #         pass


# @events.register(events.NewMessage(pattern='/start', from_users=admin_id))
# @events.register(events.NewMessage(pattern='https://t.me/', from_users=admin_id))
# @events.register(events.NewMessage(pattern=None, from_users=admin_id))
@events.register(events.NewMessage(pattern=None))
async def handler(update):
    message = update.message
    try:
        orders = trans_order(message)
        if orders:
            await add2lines(orders)
        else:
            # await bot.send_message(admin_id, '参数错误，请按照参考格式输入:\n\n'
            #                                  '<i>https://t.me/namestring </i>\n\n'
            #                                  '<i>https://t.me/namestring/100 </i>\n\n'
            #                                  '<i>https://t.me/namestring 0 </i>\n\n'
            #                                  '<i>https://t.me/namestring 0 100 </i>\n\n'
            #                                  '<i>https://t.me/namestring 0 100 video </i>\n\n'
            #                                  '<i>https://t.me/namestring 0 100 video 10 </i>\n\n'
            #                                  'Tips:最多5参数：1频道 2起始id 3下载个数 4类型 5媒体最小分钟数',
            #                        parse_mode='HTML')
            print(admin_id, '参数错误，请按照参考格式输入:\n\n'
                            '<i>https://t.me/namestring </i>\n\n'
                            '<i>https://t.me/namestring/100 </i>\n\n'
                            '<i>https://t.me/namestring 0 </i>\n\n'
                            '<i>https://t.me/namestring 0 100 </i>\n\n'
                            '<i>https://t.me/namestring 0 100 video </i>\n\n'
                            '<i>https://t.me/namestring 0 100 video 10 </i>\n\n'
                            'Tips:最多5参数：1频道 2起始id 3下载个数 4类型 5媒体最小分钟数')
            return
    finally:
        print('wait order!')


if __name__ == '__main__':
    if proxy_use:
        bot = TelegramClient('telegram_channel_downloader_bot',
                             api_id, api_hash, proxy=(socks.SOCKS5, 'localhost', socks_port)).start(
            bot_token=str(bot_token))
        client = TelegramClient(
            'telegram_channel_downloader', api_id, api_hash, proxy=(socks.SOCKS5, 'localhost', socks_port)).start()
    else:
        bot = TelegramClient('telegram_channel_downloader_bot',
                             api_id, api_hash).start(
            bot_token=str(bot_token))
        client = TelegramClient(
            'telegram_channel_downloader', api_id, api_hash).start()
    bot.add_event_handler(handler)
    tasks = []
    try:
        for i in range(max_num):
            loop = asyncio.get_event_loop()
            task = loop.create_task(worker(f'worker-{i}'))
            tasks.append(task)
        print('Successfully started (Press Ctrl+C to stop)')
        client.run_until_disconnected()
    finally:
        for task in tasks:
            task.cancel()
        client.disconnect()
        print('Stopped!')
