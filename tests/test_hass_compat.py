"""Compatibility with legacy and integration-namespaced HA MCP servers."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

spec = importlib.util.spec_from_file_location('hass_under_test', Path(__file__).resolve().parents[1] / 'src/caal/integrations/hass.py')
hass_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = hass_module
spec.loader.exec_module(hass_module)


class HACompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_namespaced_status_and_control_routing(self):
        context = "- names: Lampe salon\n  domain: light\n  state: 'off'\n  areas: Salon\n"
        client = SimpleNamespace(
            list_tools=AsyncMock(return_value=SimpleNamespace(tools=[
                SimpleNamespace(name=n) for n in ['homeassistant__GetLiveContext', 'intent__HassTurnOn']
            ])),
            call_tool=AsyncMock(return_value=SimpleNamespace(isError=False, content=[
                SimpleNamespace(text=json.dumps({'success': True, 'result': context.replace('\n', '\\n')}))
            ])),
        )
        server = SimpleNamespace(_client=client)
        mapping = await hass_module.detect_hass_tool_prefix(server)
        _, tools = hass_module.create_hass_tools(server, mapping)
        result = await tools['hass']('status', 'Lampe salon')
        self.assertIn("state: 'off'", result)
        client.call_tool.assert_awaited_with('homeassistant__GetLiveContext', {})
        await tools['hass']('turn_on', 'Lampe salon')
        self.assertEqual(client.call_tool.await_args.args[0], 'intent__HassTurnOn')

    async def test_legacy_tool_names(self):
        for prefix in ('', 'assist__'):
            client = SimpleNamespace(list_tools=AsyncMock(return_value=SimpleNamespace(tools=[
                SimpleNamespace(name=prefix+'GetLiveContext')
            ])), call_tool=AsyncMock(return_value=SimpleNamespace(isError=False,content=[])))
            server=SimpleNamespace(_client=client)
            detected=await hass_module.detect_hass_tool_prefix(server)
            _,tools=hass_module.create_hass_tools(server,detected)
            await tools['hass']('status')
            client.call_tool.assert_awaited_with(prefix+'GetLiveContext',{})

    def test_cache_supports_both_context_formats(self):
        cache=hass_module.HADeviceCache()
        cache.parse_live_context('entity_id: cover.garage\nnames: Garage\nstate: closed\narea: Garage\n')
        self.assertEqual(cache.find_device('Garage').domain,'cover')
        cache.parse_live_context(json.dumps({'result': '- names: Lampe\n  domain: light\n  state: on\n  areas: Salon\n- names: Thermostat\n  domain: climate\n  state: heat\n'}))
        self.assertEqual(len(cache.devices),2)
        self.assertEqual(cache.find_device('Lampe').area,'Salon')

if __name__ == '__main__':
    unittest.main()
