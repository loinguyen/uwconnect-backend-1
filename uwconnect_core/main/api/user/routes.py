from flask import Blueprint, make_response, redirect, request, jsonify, session
from apifairy import response, body, other_responses, arguments
from mongoengine import ValidationError
from werkzeug.exceptions import BadRequest, NotFound, Forbidden

from uwconnect_core.main.model.user import User, UserCredential
from uwconnect_core.main.service.user_service import check_login, cometchat_create_user, get_session, set_session
from uwconnect_core.main.service.utils import *
from uwconnect_core.main.api.schemas.shared_schema import MessageSchema
from uwconnect_core.main.api.schemas.user_schema import SessionSchema, UserSchema, UserAuthorizeSchema, UserDetailRequestSchema, UserCredentailSchema
from uwconnect_core.main import app

user = Blueprint('user', __name__)
message_schema = MessageSchema()
user_cre_schema = UserCredentailSchema()
user_schema = UserSchema()
user_authorize_schema = UserAuthorizeSchema()
user_request_schema = UserDetailRequestSchema()
session_schema = SessionSchema()

@user.route("/register", methods=['POST'])
@body(user_cre_schema)
@response(message_schema)
@other_responses({500: 'server error'})
def register(request):
    """
    Incoming request message:
    username/password as parameter - all will be encoded before send
    
    * need to check if the username already exist in database.
    * if the username is new then process to save the username and password to database. 
    * the account should have status as unverified.

    Return message:
    return HTTP: 200 { "message": "success" } if account created successfully
    return HTTP: 200 { "message": "exist" } if account is exist
    return server error if there is other error occurred
    """
    userData = document_to_dict(request)
    user = UserCredential(**userData)
    if UserCredential.objects(email=user.email).count() != 0:
        raise BadRequest("exist")
        
    try:
        user.validate()
    except ValidationError as e:
        print(e)
        raise BadRequest("invalid arguments")
    
    user.save()
    return { "message": "success" }


# @user.route("/validate", methods=['POST'])
@user.post("/validate")
@body(user_authorize_schema)
@response(message_schema)
@other_responses({500: 'server error'})
def validate(request):
    """
    Incoming request message:
    username/password as parameter - all will be encoded before send
    checkUserOnly flag as parameter - if this flag enable, we will check if user account exist only.

    Return message:
    process to check if username+password combination is valid
    if checkUserOnly flag is off: return { "message": "success" } if its valid account
    if checkUserOnly flag is on: return { "message": "exist" } if its valid account
    return { "message": "fail" } if its invalid account
    """

    data = request
    user_email = data['email']
    user_password = data['password']
    flag_checkUserOnly = data['checkUserOnly']

    # objects.get() is used when you are pretty sure that there is only one result. 
    # But its better to use objects.filter().first(), because it won't cause any errors. 
    if flag_checkUserOnly:
        user_query = UserCredential.objects.filter(email=user_email).first()
    else:
        user_query = UserCredential.objects.filter(email=user_email,password=user_password).first()
    
    if(user_query):
        if flag_checkUserOnly:
            return { "message": "exist" } 
        else:
            set_session("email", user_email)
            return { "message": "success" }
    else:
        return { "message": "fail" }


@user.route("/profile", methods=['GET'])
@arguments(user_request_schema)
@response(user_schema)
@check_login
def getProfile(request):
    """
    GET user profile
        Incoming request message:
            query parameter: ?email=<email address>

        Return message:
            if email does not exist: { "message": "user does not exist" }
            otherwise: { "message": "success", "body": <user object> }
    """
    # args = request.get("email")
    email = request.get("email")
    user = User.objects.filter(email=email)

    if user.count() == 0:
        raise NotFound("user does not exist")
    
    userDetail = user().first()
    del userDetail.id

    return userDetail
    

@user.route("/profile", methods=['POST'])
@body(user_schema)
@response(message_schema)
def updateProfile(request):
    """
    POST: update user detail
        Incoming request message:
            body: {
                email = EmailField(domain_whitelist=["@uwaterloo.ca"], required="true")
                username = StringField(regex="[A-Za-z0-9_ ]+", min_length=6, max_length=32)
                gender = StringField(max_length=16)
                faculty = StringField()
                program = StringField()
                year = IntField()
                courses = ListField(StringField(regex="[A-Z]+[0-9]+[A-Z]*"))
                tags = ListField(StringField())
                bio = StringField(max_length=1024)
            }

        Return Message:
            if request body does not follow the above structure: "invalid arguments"
            if email does not exist: { "message": "user does not exist" }
            otherwise: { "message": "success" }

    """
    user_email = request.email
    user_query = UserCredential.objects.filter(email=user_email)
    if (user_query.count() == 0):
        raise BadRequest("Account does not exist")
    try:
        request.validate_profile()
    except ValidationError:
        raise BadRequest("invalid arguments")
    
    user_profile_query = User.objects(email=user_email)

    # resp.set_cookie("email", request.email)
    # resp.set_cookie("username", request.username)
    set_session("email", request.email)
    set_session("username", request.username)
    # print(session)
    if user_profile_query.count() == 0:
        # new user
        uid = request.email.split('@')[0]
        cometchat_create_user(uid, request.username)

    user_profile_query.modify(upsert=True, new=True, **document_to_dict(request))
    return { "message": "success" }


@user.route("/who", methods=["GET"])
def get_logged_in_user():
    """redirect to frontend homepage if the client is not logged in"""
    print(session)
    try:
        return {
            "email": get_session("email")
        }
    except:
        # return redirect(app.config['FRONTEND_DOMAIN'] + '/')
        raise Forbidden("client not logged in")


@user.route("/test_middlewire", methods=["GET"])
@check_login
def test_middlewire():
    """
    a simple route that demonstrate how 'check_login' middlewire works, add it to protect all APIs that needs to be protected.
    All endpoints protected by 'check_login' will return 403 if no user is logged in for that client
    """
    return {"message": "success"}

