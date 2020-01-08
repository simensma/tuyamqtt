import time
import paho.mqtt.client as mqtt
import json
import tuya
from os import path
from threading import Thread
import tuyamqtt.database as database

def connack_string(state):

    states = [
        'Connection successful',
        'Connection refused - incorrect protocol version',
        'Connection refused - invalid client identifier',
        'Connection refused - server unavailable',
        'Connection refused - bad username or password',
        'Connection refused - not authorised'
    ]
    return states[state]


def payload_bool(payload:str):

        str_payload = str(payload.decode("utf-8"))
        if str_payload == 'True' or str_payload == 'ON' or str_payload == '1':
            return True       
        elif str_payload == 'False' or str_payload == 'OFF' or str_payload == '0':
            return False    
        return payload


def bool_payload(config:dict, boolvalue:bool):

    if boolvalue:
        return config['General']['payload_on']
    return config['General']['payload_off']


def bool_availability(config:dict, boolvalue:bool):

    if boolvalue:
        return config['General']['availability_online']
    return config['General']['availability_offline']


class TuyaMQTTEntity(Thread):

    delay = 0.1

    def __init__(self, key, entity, parent):        
 
        Thread.__init__(self)
        self.key = key
        # self.mqtt_topic = key
        self.entity = entity
        self.mqtt_topic = entity['topic']
        # if entity['topic'] == '':
        self.mqtt_topic = "tuya/%s/%s/%s/%s"%(entity['protocol'],entity['deviceid'],entity['localkey'],entity['ip'])

        self.parent = parent
        self.config = self.parent.config       
        self.mqtt_connected = False
        self.availability = False
        self.availability_changed = False


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
            print('Failed to connect to MQTT Broker', ex)
            self.mqtt_connected = False


    def on_message(self, client, userdata, message):      

        if message.topic[-7:] != 'command':
            return   

        print("topic",message.topic,"retained",message.retain,"message received",str(message.payload.decode("utf-8")))

        entityParts = message.topic.split("/")  
        dps_key = str(entityParts[5]) #will give problem with custom topics

        if dps_key not in self.entity['attributes']['dps']:
            self._set_dps(dps_key, None)
        if dps_key not in self.entity['attributes']['via']:
            self._set_via(dps_key, 'mqtt')
        self.set_status(dps_key, payload_bool(message.payload))

    def _set_dps(self, dps_key, dps_value:str):

        self.entity['attributes']['dps'][dps_key] = dps_value
        self.parent.set_entity_dps_item(self.key, dps_key, dps_value) 

    def _set_via(self, dps_key, via:str):

        self.entity['attributes']['via'][dps_key] = via
        self.parent.set_entity_via_item(self.key, dps_key, via) 

    def _set_availability(self, availability):

        if availability != self.availability:
            self.availability = availability
            self.availability_changed = True

    def _process_data(self, data:dict, via:str):

        changed = False
        
        for dps_key, dps_value in data['dps'].items():
            # print("_process_data",self.entity['attributes']['dps'][dps_key], dps_key, dps_value)
            if dps_key not in self.entity['attributes']['dps']:
                self._set_dps(dps_key, None)
            if dps_key not in self.entity['attributes']['via']:
                self._set_via(dps_key, 'init')
            if dps_value != self.entity['attributes']['dps'][dps_key]:
                changed = True
                self._set_dps(dps_key, dps_value)                
                self.mqtt_client.publish("%s/%s/state" % (self.mqtt_topic, dps_key),  bool_payload(self.config, dps_value))  
                
                if via != self.entity['attributes']['via'][dps_key]:                        
                    self._set_via(dps_key, via)
                
                attr_item = {
                    'dps': self.entity['attributes']['dps'][dps_key], 
                    'via': self.entity['attributes']['via'][dps_key],
                    'time': time.time()
                }
                self.mqtt_client.publish("%s/%s/attributes" % (self.mqtt_topic, dps_key),  json.dumps(attr_item))
                # print("%s/%s/attributes" % (self.mqtt_topic, dps_key))
        
        if changed:
            attr = {
                'dps': self.entity['attributes']['dps'], 
                'via': self.entity['attributes']['via'],
                'time': time.time()
            } 
            self.mqtt_client.publish("%s/attributes" % (self.mqtt_topic),  json.dumps(attr))


    def status(self, via:str = 'tuya'):
            
        try:
            data = tuya.status(self.entity)

            if not data:
                self._set_availability(False)
                return
       
            self._process_data(data, via)
            self._set_availability(True)

        except Exception as ex:
            print(ex, 'status for', self.mqtt_topic)
            self._set_availability(False)


    def set_status(self, dps_item, payload):
        # print('set_status')
        try:  
            data = tuya.set_status(self.entity, dps_item, payload)            
            # print(self.mqtt_topic, data)
            if data == None:
                self.status('mqtt')
                return

            self._process_data(data, 'mqtt')

        except Exception as ex:
            print(ex, 'set_status for', self.mqtt_topic)


    def run(self):

        time_run_availability = 0
        time_run_status = 0
        # time_unset_reset = 0  

        while True:  

            if not self.mqtt_connected:
                self.mqtt_connect()
                time.sleep(1)         

            if time.time() > time_run_status:   
                self.status()
                
                time_run_status = time.time()+self.entity['status_poll']

            if time.time() > time_run_availability:               
                time_run_availability = time.time()+15    
                if self.availability_changed:           
                    self.mqtt_client.publish("%s/availability" % self.mqtt_topic, bool_availability(self.config, self.availability)) 
                    self.availability_changed = False               
      
            # if time.time() > time_unset_reset: 
            #     time_unset_reset = time.time()+60                     
            #     self.needs_reset = False

            time.sleep(self.delay)            

   
    def on_connect(self, client, userdata, flags, rc):

        print("MQTT Connection state: %s for %s" % (connack_string(rc), self.mqtt_topic))
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

        self.database = database
        self.database.setup()        


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
            print('Failed to connect to MQTT Broker', ex)
            self.mqtt_connected = False
   

    def on_connect(self, client, userdata, flags, rc):

        print("MQTT Connection state: %s for %s" % (connack_string(rc), self.mqtt_topic))
        client.subscribe("%s/#" % self.mqtt_topic)
        self.mqtt_connected = True


    def write_entity(self):

        # try:
        #     with open(self.entities_file, 'w') as fp:
        #         json.dump(self.dictOfEntities, fp, indent=4)
        # except:
        #     print("%s not writable" % self.entities_file)  
        self.database.upsert_entities(self.dictOfEntities)


    def read_entity(self):

        # if not path.isfile(self.entities_file):
        #     print('file not found')
        #     return

        # with open(self.entities_file) as fp:
        #     self.dictOfEntities = json.loads(fp.read())

        self.dictOfEntities = self.database.get_entities()


    def add_entity_dict(self, entityRaw, retain):
        
        entityParts = entityRaw.split("/")

        key = entityParts[2]

        if key in self.dictOfEntities:
            return False
        
        entity = {
            'protocol': entityParts[1],
            'deviceid': entityParts[2],
            'localkey': entityParts[3],
            'ip': entityParts[4],
            'topic': key,            
            'attributes': {
                'dps': {},
                'via': {}
            },
            'status_poll': 5.0,
            'hass_discover': False
        }

        self.dictOfEntities[key] = entity
        # self.write_entity()
        self.database.insert_entity(entity)
        return key

    def get_entity(self, key):

        return self.dictOfEntities[key]


    def set_entity_dps_item(self, key, dps, value):

        self.dictOfEntities[key]['attributes']['dps'][dps] = value   
        self.database.update_entity(self.dictOfEntities[key])


    def set_entity_via_item(self, key, dps, value):

        self.dictOfEntities[key]['attributes']['via'][dps] = value
        self.database.update_entity(self.dictOfEntities[key])
    

    def on_message(self, client, userdata, message):                   

        if message.topic[-7:] != 'command':
            return   
        
        key = self.add_entity_dict(message.topic, message.retain)

        if key:
            print("message received",str(message.payload.decode("utf-8")),\
            "topic",message.topic,"retained",message.retain)    
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

