import http.client
import io
import json
import subprocess
import threading
import unittest
import wave
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from services.qwen_tts.server import Config, make_handler, synthesize


def wav_bytes():
    out = io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b'\0\0' * 240)
    return out.getvalue()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.config = Config('/bin/tts', '/m.gguf', '/p.gguf', '/voice.wav', 'test-key')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.config))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, payload, token='test-key'):
        connection = http.client.HTTPConnection(*self.server.server_address)
        connection.request('POST', '/v1/audio/speech', json.dumps(payload),
                           {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_auth_required(self):
        self.assertEqual(self.request({'input': 'Bonjour'}, 'wrong')[0], 401)

    def test_rejects_bad_requests(self):
        for payload in [[], {'input': ''}, {'input': 'x'*2001},
                        {'input': 'Salut', 'voice': '/etc/passwd'},
                        {'input': 'Salut', 'response_format': 'mp3'},
                        {'input': 'Salut', 'speed': 2}]:
            with self.subTest(payload=str(payload)[:60]):
                self.assertEqual(self.request(payload)[0], 400)

    def test_wav_response(self):
        with patch('services.qwen_tts.server.synthesize', return_value=wav_bytes()) as mock:
            status, audio = self.request({'input': 'Bonjour Zelda', 'model': 'qwen3-tts',
                                          'voice': 'zelda', 'response_format': 'wav', 'speed': 1})
        self.assertEqual(status, 200)
        self.assertTrue(audio.startswith(b'RIFF'))
        mock.assert_called_once_with(self.config, 'Bonjour Zelda')

    def test_timeout_and_recovery(self):
        with patch('services.qwen_tts.server.synthesize', side_effect=subprocess.TimeoutExpired('tts', 1)):
            self.assertEqual(self.request({'input': 'Bonjour'})[0], 504)
        with patch('services.qwen_tts.server.synthesize', return_value=wav_bytes()):
            self.assertEqual(self.request({'input': 'Bonjour'})[0], 200)

    def test_busy_request_does_not_start_second_gpu_process(self):
        entered, release = threading.Event(), threading.Event()
        def blocking(*_):
            entered.set()
            release.wait(5)
            return wav_bytes()
        with patch('services.qwen_tts.server.synthesize', side_effect=blocking) as mock:
            first = threading.Thread(target=lambda: self.request({'input': 'one'}))
            first.start()
            self.assertTrue(entered.wait(2))
            try:
                self.assertEqual(self.request({'input': 'two'})[0], 429)
            finally:
                release.set()
                first.join()
            self.assertEqual(mock.call_count, 1)

    def test_prompt_is_data_and_tempfiles_cleaned(self):
        seen = []
        text = '-ngl 0; $(touch /tmp/not-created) é'
        def run(command, **kwargs):
            prompt = Path(command[command.index('-f')+1])
            seen.append(prompt.parent)
            self.assertEqual(prompt.read_text(), text)
            self.assertNotIn(text, command)
            self.assertNotIn('shell', kwargs)
            Path(command[command.index('--output')+1]).write_bytes(wav_bytes())
        with patch('services.qwen_tts.server.subprocess.run', side_effect=run):
            self.assertTrue(synthesize(self.config, text).startswith(b'RIFF'))
        self.assertFalse(seen[0].exists())


if __name__ == '__main__':
    unittest.main()
