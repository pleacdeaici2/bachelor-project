import os

from constatns.Constants import path_executable


class Configuration:
    def __init__(self, json_file):
        name = json_file["filename"]
        try:
            print(os.getcwd())
            self.file_dimension = os.path.getsize(path_executable + name)
        except FileNotFoundError:
            raise FileNotFoundError(f"File {path_executable}{name} not found")
        self.name, self.extension = os.path.splitext(name)
        self.autostart = json_file["autostart"]
        self.autorestart = json_file["autorestart"]
        self.command = json_file["command"]
        self.memory = 1
