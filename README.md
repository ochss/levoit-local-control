# Levoit 200s Fan - Local Control
If you have a Levoit 200s ([https://levoit.com/products/core-200s-smart-air-purifier](https://levoit.com/products/core-200s-smart-air-purifier)) there is a way to control it without any hardware modifications. 

## Configure Home Assistant to work with Levoit
The Levoit makes use of a MQTT (`mqtt/[LEVOITID]/v2/`). All you need to do is setup a MQTT on port `1883`, add `TLS support` (self-signed is fine) and `allow_anonymous true` (no login). [This is important otherwise  Levoit wont connect]

Setup a rewrite rule for the DNS values: 
* vdmpmqtt.vesync.com pointing to your [YOUR_MQTT_SERVER] 
* *.vesync.com point to 127.0.0.1
* *.vesyncapi.com point to 127.0.0.1
* Create/update your local DNS server or use something like AdGuard to rewrite DNS entries.
* Setup your DHCP server to serve the IP address of your local DNS server to the Levoit device.
* Setup the device using the official application, but what should happen is that the device will register on to your wifi, get redirected by your DNS server and then connect to your MQTT server.
* Finally you can setup something like Home Assistant and you can control your fan.

### HA configuration example
Edit configuration.yaml and add the following (and replace [LEVOITID] with the ID of your Levoit device (find this using a MQTT client and turn on and off the device)):

```yaml
mqtt:
  button:
    - name: "Fan level 1"
      unique_id: fan_lvl_1_switch_btn
      command_topic: "mqtt/[LEVOITID]/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"id": 0,"level": 1,"type": "wind"},"method": "setLevel","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
      device_class: "restart"
    - name: "Fan level 2"
      unique_id: fan_lvl_2_switch_btn
      command_topic: "mqtt/[LEVOITID]/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"id": 0,"level": 2,"type": "wind"},"method": "setLevel","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
      device_class: "restart"
    - name: "Fan level 3"
      unique_id: fan_lvl_3_switch_btn
      command_topic: "mqtt/[LEVOITID]/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"id": 0,"level": 3,"type": "wind"},"method": "setLevel","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
      device_class: "restart"
      # sleep mode
    - name: "sleepmode"
      unique_id: fan_lvl_sleep_switch_btn
      command_topic: "mqtt/[LEVOITID]/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"mode":"sleep"},"method":"setPurifierMode","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
      device_class: "restart"
      #timer
    - name: "timer 30 min"
      unique_id: fan_lvl_timer_switch_btn
      command_topic: "mqtt/[LEVOITID]/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"action":"off","total":1800},"method":"addTimer","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
      device_class: "restart"
    - name: "display off"
      unique_id: fan_lvl_disp_off_switch_btn
      command_topic: "mqtt/[LEVOITID]/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"state":false},"method":"setDisplay","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
      device_class: "restart"
    - name: "display on"
      unique_id: fan_lvl_disp_on_switch_btn
      command_topic: "mqtt/[LEVOITID]/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"state":true},"method":"setDisplay","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
      device_class: "restart"
```


## Breakdown of payloads

Set fan to level 1

```json
{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"id": 0,"level": 1,"type": "wind"},"method": "setLevel","source": "APP"}}

```

Set fan to level 2

```json
{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"id": 0,"level": 2,"type": "wind"},"method": "setLevel","source": "APP"}}

```

Set fan to level 3

```json
{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"id": 0,"level": 3,"type": "wind"},"method": "setLevel","source": "APP"}}

```

Set sleep mode (quite operation)

```json
{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"mode":"sleep"},"method":"setPurifierMode","source": "APP"}}

```

Set timer to 30min (1800 seconds)

```json
{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"action":"off","total":1800},"method":"addTimer","source": "APP"}}
```

Get timer
```json
{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{},"method":"getTimer","source": "APP"}}
```

Delete timer
```json
{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"id":1},"method":"delTimer","source": "APP"}}
```

You should get a `rsp` from `getTimer` at `mqtt/[LEVOITID]/v2/bypass/rsp`
```json
{"traceId":"123456","code":0,"result":{"timers":[{"id":1,"remain":1749,"total":1800,"action":"off"}]}}
```

Set display off

```json
{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"state":false},"method":"setDisplay","source": "APP"}}
```

Set display on

```json
{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"state":true},"method":"setDisplay","source": "APP"}}
```

Get Schedule

```json
{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"maxId": 0},"method": "getSchedule","source": "APP"}}
```

### Example of reading a value from the MQTT broker and showing the data in HA (add to configuration.yaml)

```yaml
mqtt:
  sensor:
    - name: "Levoit Fan state"
      unique_id: "xxxx-xxxx-xxx-xxxx-xxxxx"
      state_topic: "mqtt/[LEVOITID]/v2/req"
      value_template: >-
        "{{ value_json.data.changedStatus.displayPower
        if value_json.data.changedStatus.displayPower is defined
        else value_json.data.unchangedStatus.displayPower }}"
```

### Example of response to `mqtt/[LEVOITID]/v2/req` by device to MQTT broker after an action 

You will notice that `changedStatus` registers the change that happened. 

```json
{
    "context": {
        "traceId": "1234",
        "method": "statusChangeNtyV2",
        "pid": "xxxx",
        "cid": "[LEVOITID]",
        "deviceRegion": "EU"
    },
    "data": {
        "changedStatus": {
            "switch1": "off"
        },
        "unchangedStatus": {
            "mode": "sleep",
            "displayPower": "on",
            "displayConfig": "on",
            "filterLife": 11,
            "fanSpeedLevel": 2,
            "childLock": false,
            "displayForever": false,
            "nightLightMode": "off"
        },
        "changeReason": "Device"
    }
}
```

## Levoit 100S / Vital 100S notes

The original guide targets the Levoit Core 200S. The Core 100S / Vital 100S uses the same Vesync V2 MQTT protocol, so the same DNS-redirect method applies. Differences to expect:

* **Fan levels:** The 200S uses levels 1-3. The 100S commonly supports levels 1-5. Start at level 1 and work up to find your device's max level.
* **Device ID:** The `[LEVOITID]` (the device `cid`) must be discovered per device. Use the `discover` command below.
* **Payloads:** The `setLevel`, `setPurifierMode`, `setDisplay`, `addTimer`, `getTimer`, `getSchedule` methods shown above should work on V2 devices including the 100S, but confirm each against your device's actual responses.

## Python controller (`levoit_mqtt.py`)

A small Python MQTT client is included (`levoit_mqtt.py`, requires `paho-mqtt`). It sends V2 bypass commands and can listen to discover your device ID.

Install:
```
pip install -r requirements.txt
```

1. Discover your device ID (leave it running while you press buttons in the VeSync app):
```
python levoit_mqtt.py discover --duration 30
```
Note the `cid` value printed for `NEW DEVICE ID`.

2. Control your 100S:
```
# Set fan to level 3
python levoit_mqtt.py --device-id <CID> level 3

# Enable sleep mode
python levoit_mqtt.py --device-id <CID> mode sleep

# Turn display off
python levoit_mqtt.py --device-id <CID> display off

# Add a 30-minute off timer
python levoit_mqtt.py --device-id <CID> timer off 1800

# Read timers
python levoit_mqtt.py --device-id <CID> get-timer

# Print most recent status message
python levoit_mqtt.py --device-id <CID> state
```

Options: `--host`, `--port`, `--username`, `--password`, `--tls`.

### Home Assistant example for the 100S

Replace `<LEVOITID>` with your discovered device ID. Adjust `level` values (1-5) to match what your 100S accepts.

```yaml
mqtt:
  button:
    - name: "Fan level 1"
      unique_id: fan_lvl_1_switch_btn
      command_topic: "mqtt/<LEVOITID>/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"id": 0,"level": 1,"type": "wind"},"method": "setLevel","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
    - name: "Fan level 3"
      unique_id: fan_lvl_3_switch_btn
      command_topic: "mqtt/<LEVOITID>/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"id": 0,"level": 3,"type": "wind"},"method": "setLevel","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
    - name: "sleepmode"
      unique_id: fan_lvl_sleep_switch_btn
      command_topic: "mqtt/<LEVOITID>/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode": false,"payload": {"data": {"mode":"sleep"},"method":"setPurifierMode","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
    - name: "display off"
      unique_id: fan_lvl_disp_off_switch_btn
      command_topic: "mqtt/<LEVOITID>/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"state":false},"method":"setDisplay","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
    - name: "display on"
      unique_id: fan_lvl_disp_on_switch_btn
      command_topic: "mqtt/<LEVOITID>/v2/bypass"
      payload_press: '{"traceId": "123456","method": "bypassV2","debugMode":false,"payload":{"data":{"state":true},"method":"setDisplay","source": "APP"}}'
      qos: 0
      retain: true
      entity_category: "config"
```

### Example of reading a value from the MQTT broker and showing the data in HA

```yaml
mqtt:
  sensor:
    - name: "Levoit 100S Fan state"
      unique_id: "xxxx-xxxx-xxx-xxxx-xxxxx"
      state_topic: "mqtt/<LEVOITID>/v2/req"
      value_template: >-
        "{{ value_json.data.changedStatus.displayPower
        if value_json.data.changedStatus.displayPower is defined
        else value_json.data.unchangedStatus.displayPower }}"
```

