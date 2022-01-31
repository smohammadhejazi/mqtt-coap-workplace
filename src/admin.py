import requests


class Admin:
    def __init__(self):
        self.centralAddress = 'http://localhost'
        self.centralPort = 1005
        self.token = ''

    def generateTopic(self, opcode):
        if opcode == 'office':
            return '/office/register'
        elif opcode == 'login':
            return '/admin/login'
        elif opcode == 'register':
            return '/admin/register'
        elif opcode == 'user':
            return '/admin/user/register'
        elif opcode == 'activity':
            return '/admin/user/activities'

    def generateMessageBody(self, opcode, *args):
        body = {}
        if opcode == 'office':
            body['office_name'] = args[0]
        elif opcode == 'register':
            body['office_name'] = args[0]
            body['username'] = args[1]
            body['password'] = args[2]
        elif opcode == 'login':
            body['office_name'] = args[0]
            body['username'] = args[1]
            body['password'] = args[2]
        elif opcode == 'user':
            body['token'] = self.token
            body['office_name'] = args[0]
            body['username'] = args[1]
            body['password'] = args[2]
            body['room_id'] = args[3]
        elif opcode == 'activity':
            body['token'] = self.token
            body['office_name'] = args[0]
            body['username'] = args[1]
            body['user_id'] = args[2]

        return body

    def sendRequestToCentral(self, topic, body):
        response = requests.post(self.centralAddress + ':' + str(self.centralPort) + topic,
                                 json=body)
        responseJSON = response.json()
        if topic == '/admin/login':
            self.token = responseJSON['token']
        print(responseJSON)

    def inputLoop(self):
        print('Admin Node is working, awaiting input.')
        while True:
            command = input('> ')
            commandParts = command.split(' ')
            opcode = commandParts[0]
            if opcode == 'exit':
                exit(0)
            args = commandParts[1:]

            self.sendRequestToCentral(self.generateTopic(opcode), self.generateMessageBody(opcode, *args))


if __name__ == '__main__':
    admin = Admin()
    admin.inputLoop()

