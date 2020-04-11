
import sys
import configparser

from tuyamqtt import TuyaMQTT

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(['./config/tuyamqtt.conf','/etc/tuyamqtt.conf'])

    for x in sys.argv:      
        if x == '-v' or x == '-vv' or x == '-vvv':
            config['General']['debug'] = x       

    server = TuyaMQTT(config)
 
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print ("Ctrl C - Stopping server")
        sys.exit(1)
