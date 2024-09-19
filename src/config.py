import os
from dotenv import load_dotenv


class Dotenv:
    def __init__(self):
        load_dotenv()
        self.NAME = os.getenv("NAME", "FIIT VPN")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        self.ADMIN_ID = os.getenv("ADMIN_ID", "")

        self.MZB_URL = os.getenv("MZB_URL")
        self.MZB_USERNAME = os.getenv("MZB_USERNAME")
        self.MZB_PASSWORD = os.getenv("MZB_PASSWORD")

        self.YOOMONEY_TOKEN = os.getenv("YOOMONEY_TOKEN")
        self.PRICE = float(os.getenv("PRICE", "40"))
