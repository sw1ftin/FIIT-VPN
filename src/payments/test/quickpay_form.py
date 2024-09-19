import os
from dotenv import load_dotenv
from yoomoney import Client, Quickpay

load_dotenv()

token = os.getenv("YOOMONEY_TOKEN")
price = int(os.getenv("PRICE"))
client = Client(token)

user = client.account_info()

label = ""

quickpay = Quickpay(
    receiver=user.account,
    quickpay_form="shop",
    targets="SUB 1 month",
    paymentType="SB",
    sum=100,
    label=label
)

print(quickpay.base_url)
print(quickpay.redirected_url)
