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

class TuyaMQTTStatus(Thread):


    def __init__(self, key, entity, parent, run_availability):        
 
        Thread.__init__(self)
        self.key = key
        self.entity = entity
        self.parent = parent
        self.run_availability = run_availability
        
 
    def run(self):
        availability = self.parent.config['General']['availability_offline']

        try:
            d = pytuya.OutletDevice(self.entity['id'], self.entity['ip'], self.entity['localkey'])

            if self.entity['protocol'] == '3.3':
                d.set_version(3.3)
            
            data = d.status()
            del d
            changed = False
            for dps_key, dps_item in data['dps'].items():
                if dps_key in self.parent.dictOfEntities[self.key]['dps'] and self.parent.dictOfEntities[self.key]['dps'][dps_key] != dps_item:
                    self.parent.mqtt_client.publish("%s/%s/state" % (self.key, dps_key),  self.parent.bool_payload(dps_item))   
                    self.parent.dictOfEntities[self.key]['dps'][dps_key] = dps_item    
                    changed = True            
            
            if changed:
                self.parent.mqtt_client.publish("%s/attr" % (self.key),  json.dumps(data['dps']))

            availability = self.parent.config['General']['availability_online']
            
        except Exception as ex:
            print(ex, ' status for ', self.key)
            pass

        if self.run_availability:
             self.parent.mqtt_client.publish("%s/availability" % self.key, availability)

class TuyaMQTTSetStatus(Thread):


    def __init__(self, key, entity, parent, topic, payload):        
 
        Thread.__init__(self)
        self.key = key
        self.entity = entity
        self.parent = parent
        self.topic = topic
        self.payload = payload

    
    def run(self):

        try:
            d = pytuya.OutletDevice(self.entity['id'], self.entity['ip'], self.entity['localkey'])

            if self.entity['protocol'] == '3.3':
                d.set_version(3.3)

            payload = self.payload  

            entityParts = self.topic.split("/")  
            dps_item = str(entityParts[5])

            data = d.set_status(payload, dps_item)       
            del d
        
            payload = self.parent.bool_payload(data['dps'][dps_item])

            self.parent.mqtt_client.publish("%s/%s/state" % (self.key,dps_item), payload)
            self.parent.mqtt_client.publish("%s/attr" % (self.key), json.dumps(data['dps']))
            self.parent.dictOfEntities[self.key]['dps'] = data['dps'] 
        except Exception as ex:
            print(ex, ' set_status for ', self.key)
            pass


class TuyaMQTT:


    delay = 0.1
    config = []
    dictOfEntities = {}


    def __init__(self, config):

        self.config = config

        self.entities_file = config['General']['entity_file']
        self.mqtt_topic = config['General']['topic']


    def mqtt_connect(self):  
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.enable_logger()
        self.mqtt_client.username_pw_set(self.config['MQTT']['user'], self.config['MQTT']['pass'])
        self.mqtt_client.connect(self.config['MQTT']['host'], int(self.config['MQTT']['port']), 60)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.loop_start()   
        self.mqtt_client.on_message = self.on_message        


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
            return key

        entityParts = entityRaw.split("/")
        entity = {
            'protocol': entityParts[1],
            'id': entityParts[2],
            'localkey': entityParts[3],
            'ip': entityParts[4],
            'dps': {},
        }

        self.dictOfEntities[key] = entity
        self.status(key, entity)
        #TODO: when to store?
        #if retain == 1:
        self.write_entity()
        return key

    def status(self, key, entity):

        myThreadOb1 = TuyaMQTTStatus(key, entity, self, False)           
        myThreadOb1.start()
        myThreadOb1.join()   

    def on_message(self, client, userdata, message):                   

        print("message received  ",str(message.payload.decode("utf-8")),\
            "topic",message.topic,"retained ",message.retain)
        if message.topic[-7:] != 'command':
            return        
        
        key = self.add_entity_dict(message.topic, message.retain)        
        entity = self.dictOfEntities[key]        

        myThreadOb1 = TuyaMQTTSetStatus(key, entity, self, message.topic, self.payload_bool(message.payload))            
        myThreadOb1.start()
        

    def run_states(self, run_availability = False):

        tpool = []
        for key,entity in self.dictOfEntities.items():
        
            myThreadOb1 = TuyaMQTTStatus(key, entity, self, run_availability)         
            myThreadOb1.start()
            tpool.append(myThreadOb1)   
            
        print('run_states end')


    def main_loop(self):

        """
        primary loop to send / receive from tuya devices
        """
        #quick and dirty
        time.sleep(10)
        self.mqtt_connect()
        self.read_entity()
        self.run_states()

        time_run_states = 0
        time_run_availability = 0
        run_availability = False
        time_run_save = 0
        
        while True:                       

            if time.time() > time_run_availability:               
                time_run_availability = time.time()+15
                run_availability = True
       
            if time.time() > time_run_states:                   
                self.run_states(run_availability)
                time_run_states = time.time()+5
                run_availability = False
          
            if time.time() > time_run_save:
                self.write_entity()
                time_run_save = time.time()+300

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
