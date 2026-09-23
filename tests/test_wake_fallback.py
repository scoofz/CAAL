import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock
from livekit.agents.stt import SpeechEvent, SpeechEventType, SpeechData

spec = importlib.util.spec_from_file_location('wake_test_module', Path(__file__).resolve().parents[1] / 'src/caal/stt/wake_word_gated.py')
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

class WakeFallbackTests(unittest.IsolatedAsyncioTestCase):
    def stream(self):
        stream = object.__new__(m.WakeWordGatedStream)
        stream._transcription_fallback = True
        stream._state = m.WakeWordState.LISTENING
        stream._agent_busy = False
        stream._on_state_changed = None
        stream._on_wake_detected = AsyncMock()
        self.events = []
        class Channel:
            def send_nowait(_, event): self.events.append(event)
        stream._event_ch = Channel()
        return stream

    def final(self, text):
        return SpeechEvent(SpeechEventType.FINAL_TRANSCRIPT, alternatives=[SpeechData(language='fr', text=text)])

    async def test_ambient_speech_is_not_forwarded(self):
        stream = self.stream()
        for text in ('Allume la lumière', 'Je joue à Zelda', 'Dis hey Zelda pour démarrer', 'Hey Zeldane'):
            await stream._handle_inner_event(self.final(text))
        self.assertEqual(self.events, [])
        self.assertEqual(stream._state, m.WakeWordState.LISTENING)

    async def test_wake_only_greets_without_llm_input(self):
        stream = self.stream()
        await stream._handle_inner_event(self.final('Hé, Zelda !'))
        await asyncio.sleep(0)
        stream._on_wake_detected.assert_awaited_once()
        self.assertEqual(self.events, [])
        self.assertEqual(stream._state, m.WakeWordState.ACTIVE)

    async def test_wake_and_command_preserves_only_command(self):
        stream = self.stream()
        await stream._handle_inner_event(self.final('Hey Zelda, quelle heure est-il ?'))
        self.assertEqual(self.events[-1].alternatives[0].text, 'quelle heure est-il ?')
        self.assertEqual(len(self.events), 3)
        stream._on_wake_detected.assert_not_called()
        await stream._handle_inner_event(self.final('Et demain ?'))
        self.assertEqual(self.events[-1].alternatives[0].text, 'Et demain ?')

    async def test_no_fallback_wake_while_agent_speaks(self):
        stream = self.stream()
        stream._agent_busy = True
        await stream._handle_inner_event(self.final('Hey Zelda'))
        self.assertEqual(stream._state, m.WakeWordState.LISTENING)

if __name__ == '__main__': unittest.main()
