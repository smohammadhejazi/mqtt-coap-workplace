import sys
import threading
import json
import datetime
import random
import paho.mqtt.client as paho
import asyncio
from aiocoap import *
from aiocoap.numbers.codes import Code


class Personnel:
    def __init__(self, clientType):
        self.clientType = clientType
        self.userID = -1
        self.roomID = -1
        self.token = ''

        if self.clientType == 'mqtt':
            self.brokerAddress = 'localhost'
            self.brokerPort = 1883
            self.keepAlive = 60
            self.qos = 0
            self.runMQTT()

        elif self.clientType == 'coap':
            self.localServerAddress = 'localhost'
            self.localServerPort = 5683
            self.runCOAP()

    def printLightLevel(self, light):
        now = datetime.datetime.now()
        sensor = -1
        if 8 <= now.hour <= 16:
            sensor = random.randint(66, 101)
        elif 20 < now.hour <= 24 or 0 < now.hour < 4:
            sensor = random.randint(0, 33)
        else:
            sensor = random.randint(33, 66)
        lightLevel = light - sensor
        if lightLevel > 0:
            print('Current light level: ' + str(lightLevel))
        else:
            print('Current light level: 0')

    def runMQTT(self):
        def on_message(client, userdata, message):
            payload = message.payload.decode()
            responseJSON = json.loads(payload)
            print('Response: topic: %-12s ,message: %s' % (message.topic, payload))
            if responseJSON['message'] == 'user authenticated':
                self.token = responseJSON['user_token']
                self.printLightLevel(int(responseJSON['light']))
            elif responseJSON['message'] == 'light setting updated':
                self.printLightLevel(int(responseJSON['light']))
            elif responseJSON['message'] == 'from cache':
                self.printLightLevel(int(responseJSON['light']))
            if responseJSON['message'] == 'user exited':
                exit(0)

        def serverLoop(client):
            while client.loop() == 0:
                pass

        def generateTopic(opcode):
            if opcode == 'login':
                return '/user/login'
            elif opcode == 'light':
                return '/user/' + str(self.userID)
            elif opcode == 'exit':
                return '/user/exit'

        def generateMessageBody(opcode, *args):
            body = {}
            if opcode == 'login':
                body['room_id'] = args[0]
                body['user_id'] = args[1]
                body['password'] = args[2]
                self.userID = body['user_id']
                self.roomID = body['room_id']
            elif opcode == 'light':
                body['user_token'] = self.token
                body['user_id'] = self.userID
                body['room_id'] = self.roomID
                body['light'] = args[0]
            elif opcode == 'exit':
                body['user_token'] = self.token
                body['room_id'] = self.roomID
                body['user_id'] = self.userID
            return json.dumps(body)

        def sendRequestToLocal(client, topic, messageBody):
            client.unsubscribe('/reply/$')
            client.subscribe('/reply/' + str(self.roomID))
            client.publish(topic, messageBody, self.qos)

        def inputLoop(client):
            print('Node is working, awaiting input.')
            while True:
                command = input('')
                commandParts = command.split(' ')
                opcode = commandParts[0]
                args = commandParts[1:]
                sendRequestToLocal(client, generateTopic(opcode), generateMessageBody(opcode, *args))

        client = paho.Client()
        client.on_message = on_message
        client.connect(self.brokerAddress, self.brokerPort, self.keepAlive)

        readInputThread = threading.Thread(target=inputLoop, args=(client, ))
        serverLoopThread = threading.Thread(target=serverLoop, args=(client, ))
        readInputThread.start()
        serverLoopThread.start()
        readInputThread.join()
        serverLoopThread.join()

    def runCOAP(self):
        def generateTopic(opcode):
            if opcode == 'login':
                return '/login'
            elif opcode == 'light':
                return '/light'
            elif opcode == 'exit':
                return '/exit'

        def generateMessageBody(opcode, *args):
            body = {}
            if opcode == 'login':
                body['room_id'] = args[0]
                body['user_id'] = args[1]
                body['password'] = args[2]
                self.userID = body['user_id']
                self.roomID = body['room_id']
            elif opcode == 'light':
                body['user_token'] = self.token
                body['room_id'] = self.roomID
                body['user_id'] = self.userID
                body['light'] = args[0]
            elif opcode == 'exit':
                body['user_token'] = self.token
                body['room_id'] = self.roomID
                body['user_id'] = self.userID
            return json.dumps(body)

        async def sendRequestToLocal(topic, messageBody):
            context = await Context.create_client_context()
            request = Message(code=Code.POST, payload=json.dumps(messageBody).encode(),
                              uri="coap://" + self.localServerAddress + ':' + str(self.localServerPort) + topic)
            response = await context.request(request).response
            payload = response.payload.decode().replace('\\', '').replace("\'", "\"")
            responseJSON = json.loads(payload)
            print('Response: topic: %-12s ,message: %s' % (topic, payload))
            if responseJSON['message'] == 'user authenticated':
                self.token = responseJSON['user_token']
                self.printLightLevel(int(responseJSON['light']))
            elif responseJSON['message'] == 'light setting updated':
                self.printLightLevel(int(responseJSON['light']))
            elif responseJSON['message'] == 'from cache':
                self.printLightLevel(int(responseJSON['light']))
            if responseJSON['message'] == 'user exited':
                exit(0)

        def inputLoop():
            print('Node is working, awaiting input.')
            while True:
                command = input('')
                commandParts = command.split(' ')
                opcode = commandParts[0]
                args = commandParts[1:]
                asyncio.get_event_loop().run_until_complete(
                    sendRequestToLocal(generateTopic(opcode), generateMessageBody(opcode, *args))
                )

        inputLoop()


if __name__ == '__main__':
    arguments = sys.argv
    if arguments[1] == 'mqtt':
        personnel = Personnel('mqtt')
    elif arguments[1] == 'coap':
        personnel = Personnel('coap')
    else:
        print('Error: Unknown server type.')

