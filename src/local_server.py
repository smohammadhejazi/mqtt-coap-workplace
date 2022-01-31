import sys
import requests
import json
from cachetools import TTLCache
import paho.mqtt.client as paho
import aiocoap.resource as resource
import aiocoap
import asyncio


class LocalServer:
    def __init__(self, serverType, name):
        self.serverType = serverType
        self.name = name
        self.token = ''
        self.centralAddress = 'http://localhost'
        self.centralPort = 1005
        self.cache = TTLCache(maxsize=1000, ttl=60 * 60 * 12)

        if self.serverType == 'mqtt':
            self.brokerAddress = 'localhost'
            self.brokerPort = 1883
            self.keepAlive = 60
            self.qos = 0
            self.runMQTT()

        elif self.serverType == 'coap':
            self.address = 'localhost'
            self.port = 5683
            self.runCOAP()

    def getSettingFromCache(self, userID):
        if userID in self.cache:
            return self.cache[userID]
        else:
            return None

    def sendKeyRequestToCentral(self):
        response = requests.post(self.centralAddress + ':' + str(self.centralPort) + '/office/login',
                                 json={'office_name': self.name})
        responseJSON = response.json()

        if responseJSON['message'] == 'office authenticated':
            self.token = responseJSON['office_token']
            print(responseJSON)
        else:
            print("Error: Didn't receive token")
            print(responseJSON)
            exit(-1)

    def sendRequestToCentral(self, topic, body):
        body['office_name'] = self.name
        body['office_token'] = self.token
        inCache = self.getSettingFromCache(body['user_id'])
        if topic == '/user/login' and inCache is not None:
            requests.post(self.centralAddress + ':' + str(self.centralPort) + topic,
                                     json=body)
            return {
                'message': 'from cache',
                'user_id': body['user_id'],
                'light': inCache
            }
        else:
            response = requests.post(self.centralAddress + ':' + str(self.centralPort) + topic,
                                     json=body)
            responseJSON = response.json()
            if responseJSON['message'] == 'Office token expired':
                self.sendKeyRequestToCentral()
                body['office_token'] = self.token
                response = requests.post(self.centralAddress + ':' + str(self.centralPort) + topic,
                                         json=body)
                responseJSON = response.json()
            if topic == '/user/' + str(body['user_id']):
                self.cache[body['user_id']] = responseJSON['light']
            return responseJSON

    def runMQTT(self):
        def on_message(client, userdata, message):
            messageJSON = json.loads(message.payload.decode())
            print('#' * 20)
            print('received from node:')
            print('Topic: %-20s' % message.topic)
            print('Body: %s' % str(messageJSON))

            response = self.sendRequestToCentral(message.topic, messageJSON)
            print('sending response to node: ' + str(response))
            client.publish('/reply/' + messageJSON['room_id'], json.dumps(response), self.qos)

        localServer = paho.Client()
        localServer.on_message = on_message
        localServer.connect(self.brokerAddress, self.brokerPort, self.keepAlive)
        localServer.subscribe('/user/#', self.qos)

        print('Server is running.')
        while localServer.loop() == 0:
            pass

    def runCOAP(super_self):
        class ServerResource(resource.Resource):
            def __init__(self, topic):
                super().__init__()
                self.topic = topic

            def generateCentralTopic(self, userID):
                if self.topic == 'login':
                    return '/user/login'
                elif self.topic == 'light':
                    return '/user/' + userID
                elif self.topic == 'exit':
                    return '/user/exit'

            async def render_post(self, request):
                messageJSON = json.loads(request.payload.decode().replace('\\', '')[1:-1])
                print('#' * 20)
                print('received from node:')
                print('Topic: %-20s' % self.topic)
                print('Body: %s' % str(messageJSON))
                response = super_self.sendRequestToCentral(
                    self.generateCentralTopic(messageJSON['user_id']), messageJSON
                )
                print('sending response to node: ' + str(response))
                return aiocoap.Message(payload=str(response).encode())

        root = resource.Site()
        root.add_resource(['login'], ServerResource('login'))
        root.add_resource(['light'], ServerResource('light'))
        root.add_resource(['exit'], ServerResource('exit'))
        asyncio.Task(aiocoap.Context.create_server_context(root, bind=(super_self.address, super_self.port)))
        print('Server is running.')
        asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    arguments = sys.argv
    if len(arguments) < 3:
        print('Enter server type and office name')
        exit(-1)
    if arguments[1] == 'mqtt':
        LocalServer('mqtt', arguments[2])
    elif arguments[1] == 'coap':
        LocalServer('coap', arguments[2])
    else:
        print('Error: Unknown server type.')

