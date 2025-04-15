import json


class Config:
    conf: dict = None
    __file: str = None
    __default: dict = None

    def __init__(self, file: str, default: dict = None):
        self.default = default
        self.file = "./bridge/" + file + ".json"
        try:
            with open(self.file, 'r', encoding='utf-8') as f:
                self.conf = json.load(f)
            if default is not None:
                for key in self.default.keys():
                    try:
                        self.conf[key]
                    except KeyError:
                        print("配置文件已过时，正在更新")
                        self.update()
        except Exception:
            print("配置文件异常，正在重置")
            self.data = json.dumps(default, indent=4)
            self.conf = default
            with open(self.file, 'w', encoding='utf-8') as f:
                f.write("\n" + self.data)

    def write(self, t: dict):
        try:
            self.conf.update(t)
            with open(self.file, 'w', encoding='utf-8') as f:
                data = json.dumps(self.conf, indent=4)
                f.write("\n" + data)
                f.flush()
        except Exception as e:
            print("读取配置文件异常")
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
