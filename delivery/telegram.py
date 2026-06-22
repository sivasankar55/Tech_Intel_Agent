from __future__ import annotations

import httpx

from utils.logger import setup_logger


class TelegramDeliverer:
    def __init__(self, bot_token: str, chat_id: str, chunk_size: int = 4000):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.chunk_size = chunk_size
        self.logger = setup_logger("TelegramDeliverer")
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send(self, markdown_content: str) -> bool:
        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram not configured, skipping")
            return False

        try:
            chunks = self._chunk_message(markdown_content)
            for i, chunk in enumerate(chunks):
                success = self._send_chunk(chunk)
                if not success:
                    self.logger.error(f"Failed to send chunk {i+1}/{len(chunks)}")
                    return False
                self.logger.info(f"Sent chunk {i+1}/{len(chunks)}")
            return True
        except Exception as e:
            self.logger.error(f"Telegram delivery failed: {e}")
            return False

    def _send_chunk(self, text: str) -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        try:
            resp = httpx.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                return True
            self.logger.warning(f"Telegram API error: {resp.status_code} {resp.text[:200]}")
            if resp.status_code == 400:
                payload["parse_mode"] = "HTML"
                resp2 = httpx.post(url, json=payload, timeout=30)
                return resp2.status_code == 200
            return False
        except Exception as e:
            self.logger.error(f"Telegram send error: {e}")
            return False

    def _chunk_message(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        lines = text.split("\n")
        current = []

        for line in lines:
            candidate = "\n".join(current + [line]) if current else line
            if len(candidate) > self.chunk_size:
                if current:
                    chunks.append("\n".join(current))
                    current = [line]
                else:
                    for i in range(0, len(line), self.chunk_size):
                        chunks.append(line[i : i + self.chunk_size])
            else:
                current.append(line)

        if current:
            chunks.append("\n".join(current))

        return chunks
