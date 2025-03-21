import json


class Config:
    file: str = None
    default: dict = None

    def __init__(self, file: str, default: dict = None):
        self.default = default
        self.file = "./bridge/" + file + ".json"
        try:
            with open(self.file, 'r', encoding='utf-8') as f:
                self.conf = json.load(f)
        except Exception as e:
            print("配置文件异常，正在重置")
            print("错误代码：" + str(e))
            self.data = json.dumps(default, indent=4)
            with open(self.file, 'w', encoding='utf-8') as f:
                f.write("\n" + self.data)

    def read(self):
        try:
            with open(self.file, 'r', encoding='utf-8') as f:
                self.conf = json.load(f)
            return self.conf
        except Exception as e:
            print("读取配置文件异常")
            print("错误代码：" + str(e))
            return -1

    def write(self, t: dict):
        try:
            self.conf.update(t)
            with open(self.file, 'w', encoding='utf-8') as f:
                data = json.dumps(self.conf, indent=4)
                f.write("\n" + data)
                f.flush()
        except Exception as e:
            print("读取配置文件异常")
            print("错误代码：" + str(e))
            return -1

    def wipe(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            f.write("\n" + self.data)
            f.flush()
        with open(self.file, 'r', encoding='utf-8') as f:
            self.conf = json.load(f)

    def update(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            self.default.update(self.conf)
            self.data = json.dumps(self.default, indent=4)
            f.write("\n" + self.data)
            f.flush()
        with open(self.file, 'r', encoding='utf-8') as f:
            self.conf = json.load(f)
