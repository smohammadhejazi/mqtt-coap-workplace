#  Workplace simulation using MQTT and COAP
This project wat and assignment in IOT course. It's a simulation of a workplace consisting of personnel room nodes, local server, central server and admin.

# Features
- Personnel nodes communicate with local server and local server communicate with central server. Admins can communicate with central server directly.
- Central server has a REST API that can be used to access its functionalities, namely admins can create new office (each office has a local server), new admin, new personnel, checking personnel activities and personnel nodes can login and set their light settings.
- Personnel nodes and local server can communicate with either MQTT or COAP protocol, and all the other communications are through HTTP protocol. Personnel can login and set their light setting and after each login, the new setting will be loaded.
- Local server has a TTL cache that caches personnel settings for 12 hours and can respond to personnel nodes without sending requests to central server.

### Requirements 
For running the code, first install the requirements:
```sh
pip install -r requirements.txt
```
also for using MQTT you need to run the Mosquitto broker, you can use this link to download [this](https://mosquitto.org/download/ "this") the open source broker, then execute mosquitto.exe.

You also need to install MongoDB and create 'central_server' databae with below collections:
activity, admin, admin_token, office, office_token, sequence, user, user_token
### Run the project
Now run the python codes.
local_server.py needs two env args, first is the type of connection to personnel nodes and 
and the name of the office.
personnel.py also needs the connection type from env args.
```sh
python central_server.py
python local_server.py mqtt office1 <--- this is registered office name by admin
python admin_server.py
python personnel.py mqtt
```
for coap:
```sh
python central_server.py
python local_server.py coap office1 <--- this is registered office name by admin
python admin_server.py
python personnel.py coap

```
