TuyaMQTT
==================

Listens on MQTT topic and routes requests to Tuya devices, based on a one to one topic translation. 

Quick Example
-----------
```
tuya/3.3/34280100600194d17c96/e7e9339aa82abe61/192.168.1.50/1/state
tuya/3.3/34280100600194d17c96/e7e9339aa82abe61/192.168.1.50/1/command
tuya/3.3/34280100600194d17c96/e7e9339aa82abe61/192.168.1.50/availability
tuya/3.3/34280100600194d17c96/e7e9339aa82abe61/192.168.1.50/attr
```

Installation 
-----------
```
git clone https://github.com/TradeFace/tuyamqtt.git
cd tuyamqtt
make
make install
```

Installation Docker
-----------
```
git clone https://github.com/TradeFace/tuyamqtt.git
cd tuyamqtt
make docker
```

Running Docker
------------
```
docker run -it --rm --name my-app tuyamqtt
```

Running Docker Compose
-------------
```
version: '3'
services:
  homeassistant:
    ports: 
      - "8123:8123"
    ...
    restart: always
    network_mode: host
  mosquitto:
    image: eclipse-mosquitto
    ...
    restart: always
    network_mode: host
  tuyamqtt:
    image: "tuyamqtt:latest"
    hostname: tuyamqtt 
    container_name: tuyamqtt   
    working_dir: /usr/src/app    
    volumes:
      - ./config:/usr/src/app/config    
    command: "python main.py"
    restart: always
    network_mode: host
```

MQTT Topics
===========
```
tuya/<protocol>/<device-id>/<device-localkey>/<device-ip>/<dps>/state
tuya/<protocol>/<device-id>/<device-localkey>/<device-ip>/<dps>/command
tuya/<protocol>/<device-id>/<device-localkey>/<device-ip>/attr
tuya/<protocol>/<device-id>/<device-localkey>/<device-ip>/availability
```

MQTT state
--------------
State payload values can be set in tuyamqtt.conf. Updates on command, or on state change on device (5 second polling)

- Default values: `ON`, `OFF`

MQTT command
--------------
Valid values are `true`, `ON`, `1`, `false`, `OFF`, `0`

MQTT attributes
--------------
Returns all device attributes. Updates on command, or on state change on device (5 second polling)

MQTT availability
--------------
Availability payload values can be set in tuyamqtt.conf. Updates every 15 seconds. 

- Default values: `online`, `offline`.


tuyamqtt.conf
==============
```
[General]
entity_file: ./config/entities.json
topic: tuya
payload_on: ON
payload_off: OFF
availability_online: online
availability_offline: offline

[MQTT]
user: myusername
pass: mypassword
host: 192.168.1.14
port: 1883
```


Home Assistant Example
=============
```
switch:
  - platform: mqtt
    name: "Living Socket Left 1"
    command_topic: "tuya/3.3/34280100500194d17c95/e7e9339dd82abe61/192.168.1.50/1/command"  
    state_topic: "tuya/3.3/34280100500194d17c95/e7e9339dd82abe61/192.168.1.50/1/state"
    availability_topic: "tuya/3.3/34280100500194d17c95/e7e9339dd82abe61/192.168.1.50/1/availability"
  - platform: mqtt
    name: "Living Socket Left 2"
    command_topic: "tuya/3.3/347550642cf432a2cbaf/314c6b7f3f44f979/192.168.1.51/1/command"
    state_topic: "tuya/3.3/347550642cf432a2cbaf/314c6b7f3f44f979/192.168.1.51/1/state"
    availability_topic: "tuya/3.3/347550642cf432a2cbaf/314c6b7f3f44f979/192.168.1.51/1/availability"
  - platform: mqtt
    name: "Living Socket Right 1"
    command_topic: "tuya/3.3/347550712cf432a2b04a/f9b80165db5e06bd/192.168.1.54/1/command" 
    state_topic: "tuya/3.3/347550712cf432a2b04a/f9b80165db5e06bd/192.168.1.54/1/state"
    availability_topic: "tuya/3.3/347550712cf432a2b04a/f9b80165db5e06bd/192.168.1.54/1/availability"
```
- Note: availability only works for devices known by TuyaMQTT.

TODO
===================
- check config values
- remove entities after x fails?
- device config via topic is rather crude
  - simple interface?
  - file / sqlite ?
- pytuya is a mess, clean up / rewrite?

License
====================
Free to use, copy, modify, what ever you like.