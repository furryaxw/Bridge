import csv
import json
import os
import random
import re
import threading
import time

import requests
import websocket

from config import Config

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

default = {
    "Backend_API": 'http://127.0.0.1:11234/v1/chat/completions',
    "Backend": "OpenAI",  # OpenAI Ollama
    "model": "",
    "system_prompt": "",
    "model_config": {
        "max_tokens": 2048,
        "temperature": 0.8,
    },
    "censor": [""],

    "Live2D_API": 'ws://127.0.0.1:10086/api',
    "enable_Live2D": False,
    "enable_gui": False,

    "enable_tts": False,
    "voice_list": [
        'zh-CN-XiaoxiaoNeural',  # 0 Female
        'zh-CN-XiaoyiNeural',  # 1 Female recomanded
        'zh-CN-YunjianNeural',  # 2 Male
        'zh-CN-YunxiNeural',  # 3 Male recomanded
        'zh-CN-YunxiaNeural',  # 4 Male
        'zh-CN-YunyangNeural'  # 5 Male
    ],
    "speaker": "",
    "GPT_soVITS_API": "http://127.0.0.1:9880",
    "tts_engine": "Edge_tts",  # GPT_soVITS Edge_tts

    "enable_stt": False,
    "stt_config": {
        'spinner': False,
        'model': "base",  # tiny, base, medium, large-v2
        'download_root': './bridge/model',
        'language': 'zh',
        'silero_sensitivity': 0.4,
        'webrtc_sensitivity': 2,
        'post_speech_silence_duration': 0.25,
        'min_length_of_recording': 0,
        'min_gap_between_recordings': 0,
    },
    "proxies": {
        'http': None,
        'https': None
    },
    "debug": False
}
thread_tts = threading.Thread
current_audio_thread = None
stop_audio_event = threading.Event()
pygame.mixer.init()


def post_msg(m_inp):
    global thread_response_alive
    match conf_f.conf["Backend"].lower():
        case "openai":
            msg = {"messages": m_inp}
            msg.update(conf_f.conf["model_config"])
            if conf_f.conf["model"] is not None:
                msg.update({"model": conf_f.conf["model"]})
            json_data = json.dumps(msg)
            thread_response_alive = True
            raw = requests.post(conf_f.conf["Backend_API"], data=json_data,
                                headers={'Content-Type': 'application/json'},
                                proxies=conf_f.conf["proxies"]).content
            if conf_f.conf["debug"]: print("raw: " + str(raw))
            response_msg = json.loads(raw)["choices"]
            response_sector = list(response_msg)[0]
            thread_response_alive = False
            return response_sector["message"]["content"]
        case "openai_old":
            msg = {"messages": m_inp}
            msg.update(conf_f.conf["model_config"])
            if conf_f.conf["model"] is not None:
                msg.update({"model": conf_f.conf["model"]})
            json_data = json.dumps(msg)
            thread_response_alive = True
            raw = requests.post(conf_f.conf["Backend_API"], data=json_data,
                                headers={'Content-Type': 'application/json'},
                                proxies=conf_f.conf["proxies"]).content
            if conf_f.conf["debug"]: print("raw: " + str(raw))
            response_msg = json.loads(raw)["choices"]
            response_sector = list(response_msg)[index_msg]
            thread_response_alive = False
            return response_sector["message"]["content"]
        case "ollama":
            json_data = json.dumps({
                "messages": m_inp,
                "model": conf_f.conf["model"],
                "stream": False
            })
            thread_response_alive = True
            raw = requests.post(conf_f.conf["Backend_API"] + "/api/chat", data=json_data,
                                headers={'Content-Type': 'application/json'},
                                proxies=conf_f.conf["proxies"]).content
            if conf_f.conf["debug"]: print("raw: " + str(raw))
            response_msg = json.loads(raw)["message"]["content"]
            thread_response_alive = False
            return response_msg
        case "tts_test":
            user_msg = m_inp[-1]["content"]
            return user_msg
        case _:
            raise KeyError("Unknown Backend Name")


def tts(text):
    global current_audio_thread, stop_audio_event

    if not text:
        return
    if current_audio_thread and current_audio_thread.is_alive():
        stop_audio_event.set()  # 发送终止信号
        current_audio_thread.join()  # 等待线程结束
        stop_audio_event.clear()  # 重置事件
    for file in [f for f in os.listdir(log_path) if f.endswith('.mp3')]:
        try:
            os.remove(os.path.join(log_path, file))
        except:
            pass
    text = re.sub(r"（.*?）", '', text.replace('(', '（').replace(')', '）'))

    # 生成新的音频文件路径
    audio_file = f"tts_{random.randint(1000, 9999)}.mp3"
    audio_path = os.path.join(log_path, audio_file)

    match conf_f.conf["tts_engine"].lower():
        case "edge_tts":
            import asyncio
            asyncio.run(edge_tts_backend(text, audio_path))
        case "gpt_sovits":
            sovits_api = conf_f.conf["GPT_soVITS_API"]
            url = f"{sovits_api}?text={text}&text_language=zh"
            response = requests.get(url)
            with open(audio_path, 'wb') as f:
                f.write(response.content)
        case _:
            print(f"不支持的 TTS 引擎: {conf_f.conf['tts_engine']}")
            return

    def play_audio():
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not stop_audio_event.is_set():
                pygame.time.Clock().tick(10)  # 10ms 检查一次
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        finally:
            time.sleep(1)
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except PermissionError:
                    pass

    current_audio_thread = threading.Thread(target=play_audio)
    current_audio_thread.start()


async def edge_tts_backend(text, audio_path):
    import edge_tts
    rate = '+0%'
    volume = '+0%'
    tts = edge_tts.Communicate(text=text, voice=conf_f.conf["speaker"], rate=rate, volume=volume)
    await tts.save(audio_path)


def live2d_send(response):
    ws = websocket.WebSocket()
    try:
        ws.connect(conf_f.conf["Live2D_API"])
    except Exception as e:
        print('WS异常：', e)
    msg = json.dumps({
        "msg": 11000,
        "msgId": 1,
        "data": {
            "id": 0,
            "text": response,
            "textFrameColor": 0x000000,
            "textColor": 0xFFFFFF,
            "duration": 10000
        }
    })
    ws.send(msg)
    ws.close()


def chat_main(input):
    time_start = time.time()
    global index_msg
    index_msg += 2
    try:
        from process import post_message
        input = post_message(input)
    except (ModuleNotFoundError, NameError, TypeError, ImportError):
        pass
    log.append({"role": "user", "content": input})
    with open(log_path + history_file, 'a+', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        row = ["user", input]
        writer.writerow(row)
    log_f.write("user: " + input + "\n")
    log_f.flush()
    try:
        from process import recv_message
        raw = recv_message(post_msg(log))
        if type(raw) is dict:
            llm_output = raw["output"]
            response = str(raw["raw"])
        else:
            llm_output = raw
            response = raw
    except (ModuleNotFoundError, NameError, TypeError, ImportError):
        raw = post_msg(log)
        llm_output = raw
        response = raw
    log.append({"role": "assistant", "content": response})
    with open(log_path + history_file, 'a+', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        row = ["assistant", response]
        writer.writerow(row)
    log_f.write("assistant: " + response + "\n")
    log_f.flush()
    print('time cost', (time.time() - time_start), 's')
    for c in conf_f.conf["censor"]:
        llm_output = llm_output.replace(c, '')
    output(llm_output, "AI: ")
    return llm_output


def enter_read(event):
    global thread_response_alive, thread_tts_alive
    if thread_response_alive or thread_tts_alive:
        return
    msg = gui_input.get()
    if msg != "":
        if msg[0] == "/":
            command(msg)
            gui_input.delete(0, tkinter.END)
        else:
            print("User: " + msg)
            thread_response = threading.Thread(target=chat_main, args=(msg,))
            thread_response.start()
            gui_input.delete(0, tkinter.END)


def on_click(event):
    global start_x, start_y
    start_x = event.x
    start_y = event.y


def on_move(event):
    delta_x = event.x - start_x
    delta_y = event.y - start_y
    new_x = window.winfo_x() + delta_x
    new_y = window.winfo_y() + delta_y
    window.geometry(f"+{new_x}+{new_y}")


def visibility(event):
    x, y = event.x, event.y
    # if 2 < x < 138 and 2 < y < 18:
    #     window.attributes("-alpha", 0.8)
    # else:
    #     window.attributes("-alpha", 0.2)


def command(input):
    global voice
    input = input.lower()
    command_list = input[1:].split(" ")
    if command_list[0] == "set":
        if command_list[1] == "live2d":
            if command_list[2] == "on":
                conf_f.conf["enable_Live2D"] = True
                output("Live2D发送已开启")
            elif command_list[2] == "off":
                conf_f.conf["enable_Live2D"] = False
                output("Live2D发送已关闭")
            else:
                output("未知Live2D指令")

        elif command_list[1] == "tts":
            if command_list[2] == "on":
                conf_f.conf["enable_tts"] = True
                conf_f.write({"enable_tts": True})
                output("TTS已开启")
            elif command_list[2] == "off":
                conf_f.conf["enable_tts"] = False
                conf_f.write({"enable_tts": False})
                output("TTS已关闭")
            elif int(command_list[2]) in range(0, 5):
                voice = command_list[2]
                output("TTS音源已设置为：" + voice)
            else:
                output("未知TTS指令")
    elif command_list[0] == "del":
        if command_list[2] == "logs":
            os.remove(log_path + log_file)
            for file in [f for f in os.listdir(log_path) if os.path.isfile(os.path.join(log_path, f))]:
                if file.endswith('.mp3'):
                    os.remove(os.path.join(log_path, file))
        elif command_list[2] == "history":
            os.remove(log_path + history_file)
    elif command_list[0] == "exit":
        quit()
    else:
        output("未知的指令")


def output(message, front=""):
    print(front + message)
    if conf_f.conf["enable_Live2D"]:
        live2d_send(message)
    if conf_f.conf["enable_tts"]:
        thread_tts = threading.Thread(target=tts, args=(message,))
        thread_tts.start()


if __name__ == '__main__':
    log_path = 'bridge/'
    audio_file = ''
    if not os.path.exists(log_path):
        os.makedirs(log_path)
        print("Log dir not found, creating")

    conf_f = Config('bridge', default)
    log_file = 'chat.log'
    history_file = 'history.csv'

    if os.path.exists(log_path + conf_f.conf["system_prompt"]):
        with open(log_path + conf_f.conf["system_prompt"], mode='r', encoding='utf-8') as file:
            system_prompt = file.read()
    else:
        system_prompt = conf_f.conf["system_prompt"]

    log_f = open(log_path + log_file, "a", encoding='utf-8')
    try:
        with open(log_path + history_file, mode='r', newline='', encoding='utf-8') as file:
            fieldnames = ("role", "content")
            reader = csv.DictReader(file, fieldnames)
            log = [row for row in reader][1:]
        if not log:
            raise FileNotFoundError
        if log[0]["content"] != system_prompt:
            raise FileNotFoundError
    except FileNotFoundError:
        log = [
            {"role": "system", "content": system_prompt}
        ]
        with open(log_path + history_file, mode='w', newline='', encoding='utf-8') as file:
            keys = log[0].keys()
            writer = csv.DictWriter(file, fieldnames=keys)
            writer.writeheader()
            writer.writerows(log)

    index_msg = 0
    log_f.write("system: " + system_prompt + "\n")
    log_f.flush()
    thread_response_alive = False
    thread_tts_alive = False
    if conf_f.conf["enable_stt"]:
        from RealtimeSTT import AudioToTextRecorder
        from multiprocessing import freeze_support

        freeze_support()
        print("Initializing RealtimeSTT test...")
        recorder = AudioToTextRecorder(**conf_f.conf["stt_config"])
        print("Say something...")


        def process_text(text):
            import zhconv
            msg = zhconv.convert(text, 'zh-hans')
            print("User: " + msg)
            chat_main(msg)


        def realtime_stt_daemon():
            while True:
                recorder.text(process_text)


        stt = threading.Thread(target=realtime_stt_daemon, daemon=True)
        stt.start()
    if conf_f.conf["enable_gui"]:
        import tkinter

        start_x, start_y = 0, 0
        window = tkinter.Tk()
        gui_input = tkinter.Entry(window, width=20)
        gui_move = tkinter.Button(window, text="移动", font=('黑体', 10))
        window.attributes("-alpha", 1)
        window.config(background='#2B2D30')
        gui_move.configure(bg='#1E1F22', fg='#BEBEBE')
        gui_input.configure(bg='#1E1F22', fg='#F5F5F5')
        window.overrideredirect(True)
        gui_move.pack(side=tkinter.LEFT)
        gui_input.pack(side=tkinter.RIGHT)
        window.bind('<Motion>', visibility)
        gui_move.bind('<Button-1>', on_click)
        gui_move.bind('<B1-Motion>', on_move)
        gui_input.bind("<Return>", enter_read)
        window.mainloop()
    else:
        while 1:
            usr_input = input("User：")
            while thread_tts_alive:
                time.sleep(1)
            if usr_input != "":
                if usr_input[0] == "#":
                    command(usr_input)
                else:
                    chat_main(usr_input)
