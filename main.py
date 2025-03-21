import json
import os
import threading
import time

import requests
import websocket

from config import Config

default = {
    "Backend_API": 'http://127.0.0.1:11434/api/chat',
    "Backend": "ollama",  # OpenAI ollama TTS_test
    "model": "",  # For ollama

    "Live2D_API": 'ws://127.0.0.1:10086/api',
    "enable_Live2D": False,
    "enable_gui": False,
    "system_prompt": "",

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
    "enable_tts": False,
}


def post_msg():
    global thread_response_alive
    match Backend:
        case "OpenAI":
            json_data = json.dumps({
                "messages": log,
                "max_tokens": 2000,
                "temperature": 0.9,
                "num_beams": 4,
                "top_k": 40,
                "top_p": 0.75,
                "repetition_penalty": 1.25
            })
            thread_response_alive = True
            raw = requests.post(Backend_API, data=json_data, headers={'Content-Type': 'application/json'}).content
            response_msg = json.loads(raw)["choices"]
            response_sector = list(response_msg)[index_msg]
            thread_response_alive = False
            return response_sector["message"]["content"]
        case "ollama":
            json_data = json.dumps({
                "messages": log,
                "model": model,
                "stream": False
            })
            thread_response_alive = True
            raw = requests.post(Backend_API, data=json_data, headers={'Content-Type': 'application/json'}).content
            response_msg = json.loads(raw)["message"]["content"]
            thread_response_alive = False
            return response_msg
        case "TTS_test":
            return "测试"


def tts(text):
    from playsound import playsound
    import re
    text.replace('(', '（').replace(')', '）')
    text = re.sub(r"（.*?）", '', text)
    match tts_engine:
        case "Edge_tts":
            import asyncio
            global thread_tts_alive
            thread_tts_alive = True
            asyncio.run(edge_tts_backend(text))
            playsound(log_path + audio_file)
            os.remove(log_path + audio_file)
            thread_tts_alive = False
        case "GPT_soVITS":
            import pyaudio
            url = f"{GPT_soVITS_API}?text={text}&text_language=zh"
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(2),
                            channels=1,
                            rate=32000,
                            output=True)
            response = requests.get(url, stream=True)
            for data in response.iter_content(chunk_size=1024):
                stream.write(data)
            stream.stop_stream()
            stream.close()
            p.terminate()


async def edge_tts_backend(text):
    import edge_tts
    rate = '+0%'
    volume = '+0%'
    tts = edge_tts.Communicate(text=text, voice=speaker, rate=rate, volume=volume)
    await tts.save(log_path + audio_file)


def live2d_send(response):
    ws = websocket.WebSocket()
    try:
        ws.connect(Live2D_API)
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
    log.append({"role": "user", "content": input})
    log_f.write("user: " + input + "\n")
    log_f.flush()
    response = post_msg()
    log.append({"role": "assistant", "content": response})
    log_f.write("assistant: " + response + "\n")
    log_f.flush()
    print('time cost', (time.time() - time_start), 's')
    output(response, "AI: ")
    return response


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
    # x, y = event.widget.winfo_pointerxy()
    # window.geometry("+%s+%s" % (x - 10, y - 10))
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
    global enable_Live2D, enable_tts, voice
    input = input.lower()
    command_list = input[1:].split(" ")
    if command_list[0] == "set":
        if command_list[1] == "live2d":
            if command_list[2] == "on":
                enable_Live2D = True
                output("Live2D发送已开启")
            elif command_list[2] == "off":
                enable_Live2D = False
                output("Live2D发送已关闭")
            else:
                output("未知Live2D指令")

        elif command_list[1] == "tts":
            if command_list[2] == "on":
                enable_tts = True
                output("TTS已开启")
            elif command_list[2] == "off":
                enable_tts = False
                output("TTS已关闭")
            elif int(command_list[2]) in range(0, 5):
                voice = command_list[2]
                output("TTS音源已设置为：" + voice)
            else:
                output("未知TTS指令")
    elif command_list[0] == "exit":
        quit()
    else:
        output("未知的指令")


def output(message, front=""):
    print(front + message)
    if enable_Live2D:
        live2d_send(message)
    if enable_tts:
        thread_tts = threading.Thread(target=tts, args=(message,))
        thread_tts.start()


log_path = 'bridge/'
if not os.path.exists(log_path):
    os.makedirs(log_path)
    print("Log dir not found, creating")

conf_f = Config('bridge', default)
conf = conf_f.read()
log_file = 'chat.log'
audio_file = 'tmp.mp3'
try:
    Backend_API = conf["Backend_API"]
    Backend = conf["Backend"]
    model = conf["model"]

    Live2D_API = conf["Live2D_API"]
    enable_Live2D = conf["enable_Live2D"]
    enable_gui = conf["enable_gui"]
    system_prompt = conf["system_prompt"]

    speaker = conf["speaker"]
    GPT_soVITS_API = conf["GPT_soVITS_API"]
    tts_engine = conf["tts_engine"]
    enable_tts = conf["enable_tts"]
except KeyError:
    conf_f.update()
    conf = conf_f.read()
    Backend_API = conf["Backend_API"]
    Backend = conf["Backend"]
    model = conf["model"]

    Live2D_API = conf["Live2D_API"]
    enable_Live2D = conf["enable_Live2D"]
    enable_gui = conf["enable_gui"]
    system_prompt = conf["system_prompt"]

    speaker = conf["speaker"]
    GPT_soVITS_API = conf["GPT_soVITS_API"]
    tts_engine = conf["tts_engine"]
    enable_tts = conf["enable_tts"]

log_f = open(log_path + log_file, "a", encoding='utf-8')
log = [
    {"role": "system", "content": system_prompt}
]
index_msg = 0
log_f.write("system: " + system_prompt + "\n")
log_f.flush()
thread_response_alive = False
thread_tts_alive = False
if enable_gui:
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
        # usr_input = "你好"
        while thread_tts_alive:
            time.sleep(1)
        if usr_input != "":
            if usr_input[0] == "/":
                command(usr_input)
            else:
                chat_main(usr_input)
