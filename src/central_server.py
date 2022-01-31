from flask import *
import pymongo
import json
import binascii
import datetime
import os

DATABASE = None
EXPIRATION_TIME = 600


server = Flask(__name__)


def connectToDatabase():
    global DATABASE
    try:
        mongoClient = pymongo.MongoClient('mongodb://localhost:27017/')
        central_server = mongoClient['central_server']
        addUserSequence(central_server['sequence'])
        addExpirationIndex(central_server['admin_token'])
        addExpirationIndex(central_server['office_token'])
        addExpirationIndex(central_server['user_token'])
        DATABASE = mongoClient["central_server"]
    except Exception as e:
        print(e)
        exit(-1)


def addUserSequence(collection):
    adminSequence = collection.find_one({'collection': 'user'})
    if isNone(adminSequence):
        collection.insert_one({'collection': 'user', 'id': 0})
    else:
        collection = collection.find_one({'collection': 'user'})
        if isNone(collection):
            collection.insert_one({'collection': 'user', 'id': 0})


def addExpirationIndex(collection):
    try:
        collection.drop_index('expiration_index')
    except Exception as e:
        pass
    collection.create_index('created_at', expireAfterSeconds=EXPIRATION_TIME, name='expiration_index')


def registerUser(password, office, roomID):
    adminSequence = DATABASE['sequence'].find_one_and_update({'collection': 'user'}, {"$inc": {"id": 1}}, new=True)
    newID = adminSequence['id']
    DATABASE['user'].insert_one({
        '_id': newID,
        'password': password,
        'light': -1,
        'office_name': office,
        'room_id': int(roomID)
    })


def generateToken():
    return binascii.hexlify(os.urandom(10)).decode()


def isNone(condition):
    if condition is None:
        return True
    return False


@server.route('/office/register', methods=['POST'])
def officeRegister():
    request_json = request.json
    office = request_json['office_name']
    officeInDB = DATABASE['office'].find_one({'office': office})
    if isNone(officeInDB):
        DATABASE['office'].insert_one({'office_name': office})
        return Response(json.dumps({"message": "Office created"}))
    else:
        return Response(json.dumps({"message": "Office already exists"}))


@server.route('/office/login', methods=['POST'])
def officeLogin():
    request_json = request.json
    office = request_json['office_name']
    officeInDB = DATABASE['office'].find_one({'office_name': office})
    if isNone(officeInDB):
        return Response(json.dumps({"message": "Incorrect office"}))
    else:
        randomToken = generateToken()
        DATABASE['office_token'].insert_one({
            'office_name': office,
            'token': randomToken,
            'created_at': datetime.datetime.utcnow()
        })
        return Response(json.dumps({"message": "office authenticated", "office_token": randomToken}))


@server.route('/admin/register', methods=['POST'])
def adminRegister():
    request_json = request.json
    office = request_json["office_name"]
    adminUsername = request_json["username"]
    password = request_json["password"]
    adminInDB = DATABASE['admin'].find_one({'username': adminUsername, 'office_name': office})
    if isNone(adminInDB):
        DATABASE['admin'].insert_one({
            'username': adminUsername,
            'password': password,
            'office_name': office
        })
        return Response(json.dumps({"message": "Admin register successful"}))
    else:
        return Response(json.dumps({"message": "Admin already exists"}))


@server.route('/admin/login', methods=['POST'])
def adminLogin():
    request_json = request.json
    office = request_json["office_name"]
    adminUsername = request_json["username"]
    password = request_json["password"]
    adminInDB = DATABASE['admin'].find_one({'username': adminUsername, 'password': password, 'office_name': office})
    if isNone(adminInDB):
        return Response(json.dumps({"message": "Incorrect username/password/office"}))
    else:
        randomToken = generateToken()
        DATABASE['admin_token'].insert_one({
            'username': adminUsername,
            'token': randomToken,
            'created_at': datetime.datetime.utcnow()
        })
        return Response(json.dumps({"message": "login successful", "token": randomToken}))


@server.route('/admin/user/register', methods=['POST'])
def adminUserRegister():
    request_json = request.json
    token = request_json["token"]
    office = request_json["office_name"]
    adminUsername = request_json["username"]
    password = request_json["password"]
    roomID = request_json["room_id"]

    tokenCheck = DATABASE['admin_token'].find_one({'username': adminUsername, 'token': token})
    isValidOffice = DATABASE['admin'].find_one({'username': adminUsername, 'office_name': office})
    if not isNone(tokenCheck) and not isNone(isValidOffice):
        registerUser(password, office, roomID)
        return Response(json.dumps({"message": "User register successful"}))
    else:
        return Response(json.dumps({"message": "Incorrect office/ Expired token"}))


@server.route('/admin/user/activities', methods=['POST'])
def adminUserActivities():
    request_json = request.json
    token = request_json["token"]
    office = request_json["office_name"]
    adminUsername = request_json["username"]
    userID = request_json["user_id"]

    tokenCheck = DATABASE['admin_token'].find_one({'username': adminUsername, 'token': token})
    isValidOffice = DATABASE['admin'].find_one({'username': adminUsername, 'office_name': office})
    isUserOfficeValid = DATABASE['user'].find_one({'_id': int(userID), 'office_name': office})
    if not isNone(tokenCheck) and not isNone(isValidOffice) and not isNone(isUserOfficeValid):
        userActivities = DATABASE['activity'].find({'user_id': int(userID)})
        return Response(json.dumps({
            'message': 'success',
            'activities': [{
                'user_id': activity['user_id'],
                'office_name': activity['office_name'],
                'datetime': str(activity['datetime']),
                'type': activity['type']
                } for activity in userActivities]}))
    else:
        return Response(json.dumps({'message': 'Incorrect username/office or Expired token'}))


@server.route('/user/login', methods=['POST'])
def userLogin():
    request_json = request.json
    officeToken = ''
    if 'office_token' in request_json:
        officeToken = request_json['office_token']
    office = request_json['office_name']
    userID = request_json["user_id"]
    password = request_json["password"]
    roomID = request_json["room_id"]
    officeTokenCheck = DATABASE['office_token'].find_one({'office_name': office, 'token': officeToken})
    userInDB = DATABASE['user'].find_one({'_id': int(userID), 'password': password, 'office_name': office, 'room_id': int(roomID)})
    if isNone(officeTokenCheck):
        return Response(json.dumps({'message': 'Office token expired'}))
    elif isNone(userInDB):
        return Response(json.dumps({'message': 'Incorrect username/password/office'}))
    else:
        randomToken = generateToken()
        DATABASE['activity'].insert_one({
            'user_id': int(userID),
            'office_name': office,
            'datetime': datetime.datetime.utcnow(),
            'type': 'enter'
        })
        DATABASE['user_token'].insert_one({
            'user_id': int(userID),
            'token': randomToken,
            'created_at': datetime.datetime.utcnow()
        })
        return Response(json.dumps({'message': 'user authenticated', 'light': userInDB['light'], 'user_token': randomToken}))


@server.route('/user/exit', methods=['POST'])
def userExit():
    request_json = request.json
    officeToken = ''
    userToken = ''
    if 'office_token' in request_json:
        officeToken = request_json['office_token']
    if 'user_token' in request_json:
        userToken = request_json['user_token']
    office = request_json['office_name']
    userID = request_json["user_id"]
    roomID = request_json["room_id"]
    officeTokenCheck = DATABASE['office_token'].find_one({'office_name': office, 'token': officeToken})
    userInDB = DATABASE['user'].find_one({'_id': int(userID), 'office_name': office, 'room_id': int(roomID)})
    userTokenCheck = DATABASE['user_token'].find_one({'user_id': int(userID), 'token': userToken})
    if isNone(officeTokenCheck):
        return Response(json.dumps({'message': 'Office token expired'}))
    elif isNone(userInDB):
        return Response(json.dumps({'message': 'Incorrect username/office'}))
    elif isNone(userTokenCheck):
        return Response(json.dumps({'message': 'User token expired'}))
    else:
        DATABASE['activity'].insert_one({
            'user_id': int(userID),
            'office_name': office,
            'datetime': datetime.datetime.utcnow(),
            'type': 'exit'
        })
        return Response(json.dumps({'message': 'user exited'}))


@server.route('/user/<int:userID>', methods=['POST'])
def userLight(userID):
    request_json = request.json
    officeToken = ''
    userToken = ''
    if 'office_token' in request_json:
        officeToken = request_json['office_token']
    if 'user_token' in request_json:
        userToken = request_json['user_token']
    office = request_json['office_name']
    light = request_json['light']

    officeTokenCheck = DATABASE['office_token'].find_one({'office_name': office, 'token': officeToken})
    userTokenCheck = DATABASE['user_token'].find_one({'user_id': int(userID), 'token': userToken})
    if isNone(officeTokenCheck):
        return Response(json.dumps({'message': 'Office token expired'}))
    elif not isNone(userTokenCheck):
        DATABASE['user'].update_one({'_id': int(userID)}, {'$set': {'light': int(light)}})
        return Response(json.dumps({'message': 'light setting updated', 'light': int(light)}))
    else:
        return Response(json.dumps({'message': 'Incorrect userID/password/office or user token Expired'}))


if __name__ == '__main__':
    connectToDatabase()
    server.run(host='localhost', port=1005)
