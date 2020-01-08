import sqlite3
import json

db = sqlite3.connect('tuyamqtt.db', check_same_thread=False)
cursor = db.cursor()

def disconnect():
    db.close()

def setup():
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (id INTEGER PRIMARY KEY, deviceid TEXT unique,
                        localkey TEXT, ip TEXT, protocol TEXT, topic TEXT, attributes TEXT, status_poll FLOAT, hass_discover BOOL)
    ''')  
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, name TEXT unique, value TEXT)
    ''')  
    db.commit()

    #not used yet
    settings = [
        {'name': 'mqtt_host', 'value': '192.168.1.14'},
        {'name': 'mqtt_port', 'value': '1883'},
        {'name': 'discovery_topic', 'value': 'tuya'}
    ]
    insert_settings(settings)
    # get_settings()

def get_settings():

    cursor.execute('''SELECT * FROM settings''')
    all_rows = cursor.fetchall()
    print(all_rows)
    return all_rows

def insert_setting(setting:dict):
    try:
        cursor.execute('''INSERT INTO settings(name, value)
                        VALUES(:name, :value)''',
                        setting)
        db.commit()       
    except Exception as e:
        # print(e)
        db.rollback()
        return False    
    return True

def insert_settings(settings:list):

    if False in set(map(insert_setting, settings)):
        return False 
    return True

#quick and dirty
def get_entities():

    dictOfEntities = {} 
    cursor.execute('''SELECT * FROM entities''')
    all_rows = cursor.fetchall()
    for row in all_rows:
        
        entity = {
            'id': row[0],
            'deviceid': row[1],
            'localkey': row[2],            
            'ip': row[3],
            'protocol': row[4],
            'topic': row[5],
            'attributes': json.loads(row[6]),
            'status_poll': row[7],
            'hass_discover': row[8]
        }
        dictOfEntities[row[1]] = entity
    # print(dictOfEntities)
    return dictOfEntities

def attributes_to_json(entity:dict):

    dbentity = dict(entity)
    dbentity['attributes'] = json.dumps(dbentity['attributes'])
    return dbentity

def insert_entity(entity:dict):
    # print('insert_entity')
    try:
        cursor.execute('''INSERT INTO entities(deviceid, localkey, ip, protocol, topic, attributes, status_poll)
                        VALUES(:deviceid, :localkey, :ip, :protocol, :topic, :attributes, :status_poll)''',
                        attributes_to_json(entity))
        db.commit()
        entity['id'] = cursor.lastrowid
    except Exception as e:
        # print(e)
        db.rollback()
        return False
    
    return True
    #insert attributes
    # db.commit()

def update_entity(entity:dict):
    # print('update_entity',entity)
    # dbentity = attributes_to_json(entity)
    try:
        with db:
            db.execute('''UPDATE entities 
                    SET deviceid = ?, localkey = ?, ip = ?, protocol = ?, topic = ?, attributes = ?, status_poll = ?
                    WHERE id = ?''',
                    (entity['deviceid'], entity['localkey'], entity['ip'], entity['protocol'], entity['topic'], json.dumps(entity['attributes']), entity['status_poll'], entity['id'])
                    )
    except Exception as e:
        # print(e)
        return False
    return True


def upsert_entity(entity:dict):
    # print(entity)      
    if not insert_entity(entity):
        return update_entity(entity)


def upsert_entities(entities:dict):
 
    if False in set(map(upsert_entity, entities.values())):
        return False 
    return True
    

def delete_entity(entity:dict):

    cursor.execute('''DELETE FROM entities WHERE id = ? ''', (entity['id'],))
    #delete attributes
    db.commit()
