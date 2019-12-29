init:
	rm -rf pythontuya
	git clone https://github.com/TradeFace/python-tuya.git pythontuya
	pip3 install -r requirements.txt

install:
	sudo sed  's|{path}|'${PWD}'|' ./config/tuyamqtt.service > /etc/systemd/system/tuyamqtt.service
	sudo cp ./config/tuyamqtt.conf /etc/tuyamqtt.conf
	sudo systemctl enable tuyamqtt.service
	sudo systemctl start tuyamqtt.service

docker:
	rm -rf pythontuya
	git clone https://github.com/TradeFace/python-tuya.git pythontuya
	docker build -t tuyamqtt .