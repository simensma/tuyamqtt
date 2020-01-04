init:
	rm -rf tuya
	git clone https://github.com/TradeFace/tuya.git tuya
	pip3 install -r requirements.txt

install:
	sudo sed  's|{path}|'${PWD}'|' ./config/tuyamqtt.service > /etc/systemd/system/tuyamqtt.service
	sudo cp ./config/tuyamqtt.conf /etc/tuyamqtt.conf
	sudo systemctl enable tuyamqtt.service
	sudo systemctl start tuyamqtt.service

docker:
	rm -rf tuya
	git clone https://github.com/TradeFace/tuya.git tuya
	docker build -t tuyamqtt .