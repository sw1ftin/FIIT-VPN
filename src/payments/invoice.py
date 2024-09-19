from yoomoney import Quickpay, Client
from uuid import uuid4


class Payment:
    def __init__(self, invoice_uuid, payment, url):
        self.invoice_uuid = invoice_uuid
        self.payment = payment
        self.url = url


class Invoice:
    def __init__(self, client: Client, price: int) -> None:
        self.client = client
        self.receiver = client.account_info().account
        self.price = int(price)

    def create(self) -> Payment:
        invoice_uuid = str(uuid4())
        payment = Quickpay(
            receiver=self.receiver,
            quickpay_form="shop",
            targets="SUB 1 month",
            paymentType="SB",
            sum=self.price,
            label=invoice_uuid
        )
        return Payment(
            invoice_uuid=invoice_uuid,
            payment=payment,
            url=payment.redirected_url
        )

    def check(self, invoice_uuid: str) -> bool:
        _history = self.client.operation_history(label=invoice_uuid)
        if _history.operations:
            for _operation in _history.operations:
                if _operation.status == "success":
                    return True
        return False
