
import sys
import configparser

from tuyamqtt import TuyaMQTT

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(['./config/tuyamqtt.conf','/etc/tuyamqtt.conf'])

    server = TuyaMQTT(config)
 
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print ("Ctrl C - Stopping server")
        sys.exit(1)
