import time
import paho.mqtt.client as mqtt
import json
import pythontuya.pytuya as pytuya
from os import path

"""
TODO:
- what about the heartbeat; now state call
"""

class TuyaMQTT:

    delay = 0.1
    config = []
    dictOfEntities = {}
    mainWait = False

    def __init__(self, config):

        self.config = config

        self.entities_file = config['General']['entity_file']
        
        self.mqtt_topic = config['General']['topic']
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.enable_logger()
        self.mqtt_client.username_pw_set(config['MQTT']['user'], config['MQTT']['pass'])
        self.mqtt_client.connect(config['MQTT']['host'], int(config['MQTT']['port']), 60)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.loop_start()   
        self.mqtt_client.on_message = self.on_message

        self.read_entity()
        self.run_states()


    def payload_bool(self, payload):

        str_payload = str(payload.decode("utf-8"))
        if str_payload == 'True' or str_payload == 'ON' or str_payload == '1':
            return True       
        elif str_payload == 'False' or str_payload == 'OFF' or str_payload == '0':
            return False    
        return payload


    def write_entity(self):

        try:
            with open(self.entities_file, 'w') as fp:
                json.dump(self.dictOfEntities, fp, indent=4)
        except:
            print("%s not writable" % self.entities_file)        

    def read_entity(self):

        if not path.isfile(self.entities_file):
            print('file not found')
            return

        with open(self.entities_file) as fp:
            self.dictOfEntities = json.loads(fp.read())


    def add_entity_dict(self, entityRaw, retain):
        
        key = entityRaw[0:-8]

        if key in self.dictOfEntities:
            return key

        entityParts = entityRaw.split("/")
        entity = {
            'protocol': entityParts[1],
            'id': entityParts[2],
            'localkey': entityParts[3],
            'ip': entityParts[4],
            'dps': entityParts[5],
            'value': None
        }

        self.dictOfEntities[key] = entity

        #TODO: when to store?
        #if retain == 1:
        self.write_entity()
        return key


    def on_message(self, client, userdata, message):                   
                
        if message.topic[-7:] != 'command':
            self.mainWait = False
            return        
        self.mainWait = True

        print("message received  ",str(message.payload.decode("utf-8")),\
            "topic",message.topic,"retained ",message.retain)
        # if message.retain==1:
        #     print("This is a retained message")  
        
        key = self.add_entity_dict(message.topic, message.retain)        
        entity = self.dictOfEntities[key]        

        try:
            d = pytuya.OutletDevice(entity['id'], entity['ip'], entity['localkey'])
            
            if entity['protocol'] == '3.3':
                d.set_version(3.3) 
        
            payload = self.payload_bool(message.payload)       
            d.set_status(payload, entity['dps'])

            data = d.status()
            self.mqtt_client.publish("%s/state" % key, data['dps'][entity['dps']])
            self.dictOfEntities[key]['value'] = data['dps'][entity['dps']]
            #close the connection
            del d
        except:
            pass

        self.mainWait = False

    def run_states(self):

        for key,entity in self.dictOfEntities.items():

            availability = 'offline'

            try:
                d = pytuya.OutletDevice(entity['id'], entity['ip'], entity['localkey'])

                if entity['protocol'] == '3.3':
                    d.set_version(3.3)

                availability = 'online'
                
                data = d.status()
                if self.dictOfEntities[key]['value'] != data['dps'][entity['dps']]:
                    
                    self.mqtt_client.publish("%s/state" % key, data['dps'][entity['dps']])
                    self.dictOfEntities[key]['value'] = data['dps'][entity['dps']]

                #close the connection
                del d
            except:
                pass
            #     data = d.online()
            self.mqtt_client.publish("%s/availability" % key, availability)  

            #as dict grows not all states might be checked when a command comes in   
            while self.mainWait:
                time.sleep(self.delay)                 


    def main_loop(self):

        """
        primary loop to send / receive from tuya devices
        """
        runStates = False
        while True:
            #we don't want to run status call when commands are comming in.
            while self.mainWait:
                time.sleep(self.delay)                         

            if round(time.time())%5 == 0 and runStates:                   
                self.run_states()
                runStates = False
            else:
                runStates = True

            time.sleep(self.delay)


    def connack_string(self, state):

        states = [
            'Connection successful',
            'Connection refused - incorrect protocol version',
            'Connection refused - invalid client identifier',
            'Connection refused - server unavailable',
            'Connection refused - bad username or password',
            'Connection refused - not authorised'
        ]
        return states[state]


    def on_connect(self, client, userdata, flags, rc):

        print("MQTT Connection state: %s" % self.connack_string(rc))
        client.subscribe("%s/#" % self.mqtt_topic)
