"""Create an isolated local profile. Never overwrite existing credentials/settings."""
import argparse
import json
import secrets
import shlex
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--host-ip', required=True, help='LAN IPv4 of this CachyOS VM')
parser.add_argument('--speaker', required=True)
parser.add_argument('--tts-bin', required=True)
parser.add_argument('--tts-model', required=True)
parser.add_argument('--tts-mmproj', required=True)
parser.add_argument('--bonsai-server', required=True)
parser.add_argument('--bonsai-model', required=True)
parser.add_argument('--ha-url', default='http://homeassistant.local:8123')
args = parser.parse_args()
import ipaddress
ipaddress.IPv4Address(args.host_ip)
root = Path(__file__).resolve().parents[1]
local = root / '.local'
local.mkdir(mode=0o700, exist_ok=True)
for name in ['zelda.env', 'settings.json']:
    if (local / name).exists():
        parser.error(f'{local / name} already exists; edit it instead of overwriting')
for name in ['speaker', 'tts_bin', 'tts_model', 'tts_mmproj', 'bonsai_server', 'bonsai_model']:
    value = Path(getattr(args, name)).expanduser().resolve()
    if not value.is_file():
        parser.error(f'{name}: file not found: {value}')
    setattr(args, name, str(value))
values = {
    'CAAL_HOST_IP': args.host_ip, 'QWEN_TTS_HOST': args.host_ip,
    'LIVEKIT_API_KEY': 'devkey', 'LIVEKIT_API_SECRET': 'secret',
    'QWEN_TTS_URL': f'http://{args.host_ip}:8890/v1',
    'QWEN_TTS_BIN': args.tts_bin, 'QWEN_TTS_MODEL': args.tts_model,
    'QWEN_TTS_MMPROJ': args.tts_mmproj, 'QWEN_TTS_SPEAKER': args.speaker,
    'QWEN_TTS_API_KEY': secrets.token_urlsafe(32), 'QWEN_TTS_CONTEXT': '2048',
    'BONSAI_HOST': args.host_ip, 'BONSAI_SERVER': args.bonsai_server,
    'BONSAI_MODEL': args.bonsai_model, 'OPENAI_API_KEY': secrets.token_urlsafe(32),
    'WHISPER_MODEL': 'Systran/faster-whisper-small', 'TIMEZONE': 'Europe/Paris',
}
env = local / 'zelda.env'
env.touch(mode=0o600)
env.write_text(''.join(f'{key}={shlex.quote(value)}\n' for key, value in values.items()))
settings = {
    'first_launch_completed': True, 'agent_name': 'Zelda', 'language': 'fr',
    'stt_provider': 'speaches', 'tts_provider': 'qwen3',
    'llm_provider': 'openai_compatible',
    'openai_base_url': f'http://{args.host_ip}:8081/v1', 'openai_model': 'zelda-bonsai',
    'openai_api_key': values['OPENAI_API_KEY'], 'num_ctx': 4096,
    'hass_host': args.ha_url, 'hass_enabled': False,
    'wake_word_model': 'models/hey_zelda.onnx', 'wake_word_enabled': True,
    'n8n_enabled': False,
}
path = local / 'settings.json'
path.touch(mode=0o600)
path.write_text(json.dumps(settings, ensure_ascii=False, indent=2)+'\n')
print('Created .local/zelda.env and .local/settings.json. Home Assistant awaits its token in Settings.')
