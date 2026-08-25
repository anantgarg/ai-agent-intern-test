import json
import logging

class JsonLogger:
    def __init__(self):
        self.log = logging.getLogger("aster-row")
        if not self.log.handlers:
            handler = logging.StreamHandler()
            self.log.addHandler(handler)
            self.log.setLevel(logging.INFO)

    def event(self, name: str, **data):
        forbidden = {"email", "address", "shipping_address", "password", "api_key", "secret", "risk_score", "internal"}
        safe = {k:v for k,v in data.items() if k not in forbidden}
        self.log.info(json.dumps({"event":name, **safe}, default=str))
