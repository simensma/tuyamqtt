import time
import paho.mqtt.client as mqtt
import json
import pythontuya.pytuya as pytuya
from os import path
from threading import Thread

import concurrent.futures
"""
TODO:
- what about the heartbeat; now state call
"""
class TuyaMQTTEntity(Thread):

    delay = 0.1

    def __init__(self, key, entity, parent):        
 
        Thread.__init__(self)
        self.key = key
        self.mqtt_topic = key
        self.entity = entity
        self.parent = parent
        self.config = self.parent.config
        self.tuya_connected = False
        self.tuya_connection = None
        self.needs_reset = False
        self.mqtt_connected = False


    def mqtt_connect(self): 

        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.enable_logger()
            self.mqtt_client.username_pw_set(self.config['MQTT']['user'], self.config['MQTT']['pass'])
            self.mqtt_client.connect(self.config['MQTT']['host'], int(self.config['MQTT']['port']), 60)
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.loop_start()   
            self.mqtt_client.on_message = self.on_message
        except Exception as ex:
            print('Failed to connect to MQTT Broker')
            self.mqtt_connected = False


    def tuya_connect(self):
        
        try:
            self.tuya_connection = pytuya.OutletDevice(self.entity['id'], self.entity['ip'], self.entity['localkey'])

            if self.entity['protocol'] == '3.3':
                self.tuya_connection.set_version(3.3)
            
            self.availability = True
            self.tuya_connected = True

        except Exception as ex:
            print(ex, 'for', self.key)
            self.availability = False
            self.tuya_connected = False
            pass    

   
    def tuya_reset(self):

        del self.tuya_connection
        self.tuya_connect()
        time.sleep(1)


    def payload_bool(self, payload):

        str_payload = str(payload.decode("utf-8"))
        if str_payload == 'True' or str_payload == 'ON' or str_payload == '1':
            return True       
        elif str_payload == 'False' or str_payload == 'OFF' or str_payload == '0':
            return False    
        return payload


    def bool_payload(self, boolvalue):

        if boolvalue:
            return self.config['General']['payload_on']
        return self.config['General']['payload_off']


    def bool_availability(self, boolvalue):

        if boolvalue:
            return self.config['General']['availability_online']
        return self.config['General']['availability_offline']


    def on_message(self, client, userdata, message):      

        if message.topic[-7:] != 'command':
            return   

        print("topic",message.topic,"retained ",message.retain,"message received  ",str(message.payload.decode("utf-8")))

        entityParts = message.topic.split("/")  
        dps_item = str(entityParts[5])

        self.set_status(dps_item, self.payload_bool(message.payload))


    def status(self, publish = True):
            
        try:
            if not self.tuya_connected or self.needs_reset:
                self.tuya_reset() 

            data = self.tuya_connection.status()

            if data == b'':
                self.needs_reset = True 
                self.status()
                return

            if type(data) is bytes:
                self.tuya_reset()               
                self.status()
                return
        
            for dps_key, dps_item in data['dps'].items():
                if publish:
                    self.mqtt_client.publish("%s/%s/state" % (self.key, dps_key),  self.bool_payload(dps_item))   
                self.parent.set_entity_dps_item(self.key, dps_key, dps_item)    
            
            if publish:
                self.mqtt_client.publish("%s/attr" % (self.key),  json.dumps(data['dps']))

            self.availability = True

        except Exception as ex:
            print(ex, 'status for', self.key)
            self.availability = False


    def set_status(self, dps_item, payload):

        data = None
        try:  
            if not self.tuya_connected or self.needs_reset:
                self.tuya_reset() 

            data = self.tuya_connection.set_status(payload, dps_item)

            if type(data) is bytes:
                self.tuya_reset()    
                self.set_status(dps_item, payload)
                return

            if dps_item not in data['dps']:
                data = self.status(False)
        
            bpayload = self.bool_payload(data['dps'][dps_item])

            self.mqtt_client.publish("%s/%s/state" % (self.key, dps_item), bpayload)
            self.mqtt_client.publish("%s/attr" % (self.key), json.dumps(data['dps']))
            self.parent.set_entity_dps_item(self.key, dps_item, payload) 
            
        except Exception as ex:
            print(ex, 'set_status for', self.key, data)


    def run(self):

        time_run_availability = 0
        time_run_status = 0
        time_unset_reset = 0       
        self.mqtt_connect()

        while True:  

            if not self.mqtt_connected:
                self.mqtt_connect()
                time.sleep(2)
                continue

            if time.time() > time_run_status:   
                self.status()
                
                time_run_status = time.time()+5

            if time.time() > time_run_availability:               
                time_run_availability = time.time()+15               
                self.mqtt_client.publish("%s/availability" % self.key, self.bool_availability(self.availability))                
                # print(self.key,"i am up")

            if time.time() > time_unset_reset: 
                time_unset_reset = time.time()+60                     
                self.needs_reset = False

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

        print("MQTT Connection state: %s for %s" % (self.connack_string(rc), self.mqtt_topic))
        client.subscribe("%s/#" % self.mqtt_topic)
        self.mqtt_connected = True


class TuyaMQTT:


    delay = 0.1
    config = []
    dictOfEntities = {}


    def __init__(self, config):

        self.config = config

        self.entities_file = config['General']['entity_file']
        self.mqtt_topic = config['General']['topic']
        self.mqtt_connected = False


    def mqtt_connect(self): 

        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.enable_logger()
            self.mqtt_client.username_pw_set(self.config['MQTT']['user'], self.config['MQTT']['pass'])
            self.mqtt_client.connect(self.config['MQTT']['host'], int(self.config['MQTT']['port']), 60)
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.loop_start()   
            self.mqtt_client.on_message = self.on_message
        except Exception as ex:
            print('Failed to connect to MQTT Broker')
            self.mqtt_connected = False

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

        print("MQTT Connection state: %s for %s" % (self.connack_string(rc), self.mqtt_topic))
        client.subscribe("%s/#" % self.mqtt_topic)
        self.mqtt_connected = True


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
        
        key = entityRaw[0:-10]

        if key in self.dictOfEntities:
            return False

        entityParts = entityRaw.split("/")
        entity = {
            'protocol': entityParts[1],
            'id': entityParts[2],
            'localkey': entityParts[3],
            'ip': entityParts[4],
            'dps': {},
        }

        self.dictOfEntities[key] = entity
        self.write_entity()
        return key

    def get_entity(self, key):

        return self.dictOfEntities[key]


    def set_entity_dps_item(self, key, dps, value):

        self.dictOfEntities[key]['dps'][dps] = value
    

    def on_message(self, client, userdata, message):                   

        if message.topic[-7:] != 'command':
            return   

        print("message received  ",str(message.payload.decode("utf-8")),\
            "topic",message.topic,"retained ",message.retain)     
        
        key = self.add_entity_dict(message.topic, message.retain)

        if key:
            entity = self.get_entity(key)
            myThreadOb1 = TuyaMQTTEntity(key, entity, self)     
            myThreadOb1.setName(key)    
            myThreadOb1.start()


    def main_loop(self):

        """
        primary loop to send / receive from tuya devices
        """
        self.read_entity()
        tpool = []
        for key,entity in self.dictOfEntities.items():
            myThreadOb1 = TuyaMQTTEntity(key, entity, self)     
            myThreadOb1.setName(key)    
            myThreadOb1.start()
            tpool.append(myThreadOb1)
 
        time_run_save = 0
        
        while True: 

            if not self.mqtt_connected:
                self.mqtt_connect()
                time.sleep(2)
                continue                      
          
            if time.time() > time_run_save:
                self.write_entity()
                time_run_save = time.time()+300

            time.sleep(self.delay)           

