"""Local OpenAI speech endpoint backed by llama-tts (standard library only).

One synthesis at a time bounds GPU memory use. The reference voice and models
are administrator-configured; HTTP clients cannot select files or CLI flags.
"""
from __future__ import annotations

import hmac
import io
import json
import os
import subprocess
import tempfile
import threading
import wave
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


@dataclass(frozen=True)
class Config:
    binary: str
    model: str
    projector: str
    speaker: str
    api_key: str
    language: str = "fr"
    context: int = 2048
    timeout: int = 120

    def validate(self):
        for name in ("binary", "model", "projector", "speaker"):
            if not Path(getattr(self, name)).is_file():
                raise ValueError(f"Missing {name}: {getattr(self, name)}")
        if not os.access(self.binary, os.X_OK):
            raise ValueError("QWEN_TTS_BIN must be executable")
        if not self.api_key:
            raise ValueError("QWEN_TTS_API_KEY is required")


def synthesize(config: Config, text: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="zelda-tts-") as directory:
        prompt = Path(directory) / "prompt.txt"
        output = Path(directory) / "speech.wav"
        prompt.write_text(text, encoding="utf-8")
        # A prompt file also handles text beginning with '-' without flag ambiguity.
        command = [config.binary, "-m", config.model, "-mm", config.projector,
                   "-ngl", "99", "-c", str(config.context), "--tts-lang", config.language,
                   "--tts-speaker-file", config.speaker, "-f", str(prompt),
                   "--output", str(output)]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, timeout=config.timeout)
        audio = output.read_bytes()
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (24000, 1, 2):
                raise ValueError("Expected mono PCM16 audio at 24000 Hz")
        return audio


def make_handler(config: Config):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def error(self, status, message):
            self.reply(status, json.dumps({"error": message}).encode())

        def authorized(self):
            return hmac.compare_digest(self.headers.get("Authorization", ""),
                                       f"Bearer {config.api_key}")

        def do_GET(self):
            if self.path == "/health":
                self.reply(200, b'{"status":"ok"}')
            elif not self.authorized():
                self.error(401, "Unauthorized")
            elif self.path == "/v1/audio/voices":
                self.reply(200, b'{"voices":["zelda"]}')
            else:
                self.error(404, "Not found")

        def do_POST(self):
            if not self.authorized():
                self.error(401, "Unauthorized")
                return
            if self.path != "/v1/audio/speech":
                self.error(404, "Not found")
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 32768:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("Expected a JSON object")
                text = payload.get("input")
                if not isinstance(text, str) or not text.strip() or len(text) > 2000:
                    raise ValueError("input must contain 1–2000 characters")
                if payload.get("model", "qwen3-tts") != "qwen3-tts":
                    raise ValueError("Unknown model")
                if payload.get("voice", "zelda") != "zelda":
                    raise ValueError("Unknown voice")
                if payload.get("response_format", "wav") != "wav":
                    raise ValueError("Only wav is supported")
                if payload.get("speed", 1.0) != 1.0:
                    raise ValueError("Only speed=1 is supported")
            except (ValueError, TypeError, UnicodeDecodeError) as exc:
                self.error(400, str(exc))
                return
            if not lock.acquire(blocking=False):
                self.error(429, "Synthesis busy; retry shortly")
                return
            try:
                audio = synthesize(config, text)
                self.reply(200, audio, "audio/wav")
            except subprocess.TimeoutExpired:
                self.error(504, "Synthesis timed out")
            except (subprocess.CalledProcessError, OSError, ValueError, wave.Error):
                self.error(502, "Synthesis failed; check server model and audio configuration")
            finally:
                lock.release()

    return Handler


def main():
    config = Config(binary=os.environ["QWEN_TTS_BIN"], model=os.environ["QWEN_TTS_MODEL"],
                    projector=os.environ["QWEN_TTS_MMPROJ"], speaker=os.environ["QWEN_TTS_SPEAKER"],
                    api_key=os.environ["QWEN_TTS_API_KEY"],
                    language=os.getenv("QWEN_TTS_LANGUAGE", "fr"),
                    context=int(os.getenv("QWEN_TTS_CONTEXT", "2048")))
    config.validate()
    address = (os.getenv("QWEN_TTS_HOST", "127.0.0.1"), int(os.getenv("QWEN_TTS_PORT", "8890")))
    server = ThreadingHTTPServer(address, make_handler(config))
    print(f"Qwen3-TTS ready on {address[0]}:{address[1]}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
