#!/usr/bin/env python3
"""Static regression checks for MVC field types and browser-side LCD limits."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src/opnsense/mvc/app/models/OPNsense/SophosFrontpanel/SophosFrontpanel.xml"
FORM = ROOT / "src/opnsense/mvc/app/controllers/OPNsense/SophosFrontpanel/forms/general.xml"
VIEW = ROOT / "src/opnsense/mvc/app/views/OPNsense/SophosFrontpanel/index.volt"
ACTIONS = ROOT / "src/opnsense/service/conf/actions.d/actions_sophos_frontpanel.conf"

model = ET.parse(MODEL).getroot()
form = ET.parse(FORM).getroot()
view = VIEW.read_text()
actions = ACTIONS.read_text()

items = model.find("items/general")
assert items is not None

device = items.find("device")
assert device is not None and device.attrib.get("type") == "JsonKeyValueStoreField"
assert device.findtext("ConfigdPopulateAct") == "sophos_frontpanel list_serial_devices"

for field_name in ("wanInterface", "lanInterface"):
    field = items.find(field_name)
    assert field is not None and field.attrib.get("type") == "InterfaceField", field_name
    assert field.findtext("Multiple") == "Y", field_name

for field_name in ("wanUseDescription", "lanUseDescription"):
    field = items.find(field_name)
    assert field is not None and field.attrib.get("type") == "BooleanField", field_name
    assert field.findtext("Default") == "1", field_name

# Server-side title validation must remain 1..16, while the browser must refuse
# more than 16 keystrokes/pasted characters as a UX guard.
title = items.find("title")
assert title is not None
mask = title.findtext("Mask") or ""
assert "{1,16}" in mask, mask
assert "setAttribute('maxlength', '16')" in view

form_fields = {f.findtext("id"): f.findtext("type") for f in form.findall("field") if f.findtext("id")}
assert form_fields["sophosfrontpanel.general.device"] == "dropdown"
assert form_fields["sophosfrontpanel.general.wanInterface"] == "select_multiple"
assert form_fields["sophosfrontpanel.general.lanInterface"] == "select_multiple"
assert form_fields["sophosfrontpanel.general.wanUseDescription"] == "checkbox"
assert form_fields["sophosfrontpanel.general.lanUseDescription"] == "checkbox"

assert "[list_serial_devices]" in actions
assert "list_serial_devices.py" in actions

print("OK: MVC schema enforces 16-char title, dynamic serial dropdown, WAN/LAN multi-selects and Description toggles")
