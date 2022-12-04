from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_jwt,
    jwt_required,
)
from passlib.hash import pbkdf2_sha256
from marshmallow import ValidationError

from models import User
from schemas.user import UserSchema
from blocklist import BLOCKLIST

_user_parser = reqparse.RequestParser()
_user_parser.add_argument(
    "username", type=str, required=True, help="This field cannot be blank."
)
_user_parser.add_argument(
    "email", type=str, required=True, help="This field cannot be blank."
)
_user_parser.add_argument(
    "password", type=str, required=True, help="This field cannot be blank."
)


_login_parser = reqparse.RequestParser()
_login_parser.add_argument(
    "username", type=str, required=True, help="This field cannot be blank."
)
_login_parser.add_argument(
    "password", type=str, required=True, help="This field cannot be blank."
)


user_schema = UserSchema()

class UserRegister(Resource):
    def post(self):
        #data = _user_parser.parse_args()
        
        try:
            user = user_schema.load(request.get_json())
        except ValidationError as err:
            return err.messages, 400

        if User.query.filter_by(username = user.username).first():
            return {"message": "A user with that username already exists"}, 400

        # user = User(
        #     username=user.username, 
        #     email = user.email,
        #     password=pbkdf2_sha256.hash(user.password)
        # )
        user.password=pbkdf2_sha256.hash(user.password)
        user.save_to_db()

        return {"message": "User created successfully."}, 201


class UserLogin(Resource):
    def post(self):
        # data = _login_parser.parse_args()
        
        try:
            userdata = user_schema.load(request.get_json())
        except ValidationError as err:
            return err.messages, 400

        user = User.query.filter_by(username = userdata.username).first()
        print(user)

        if user and pbkdf2_sha256.verify(userdata.password, user.password):
            access_token = create_access_token(identity=user.id, fresh=True)
            refresh_token = create_refresh_token(user.id)
            return {"access_token": access_token, "refresh_token": refresh_token, "user":user_schema.dump(user)}, 200

        return {"message": "Invalid Credentials!"}, 401
        #print(user)


class UserLogout(Resource):
    @jwt_required()
    def post(self):
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return {"message": "Successfully logged out"}, 200


class UserApi(Resource):
    """
    This resource can be useful when testing our Flask app.
    We may not want to expose it to public users, but for the
    sake of demonstration in this course, it can be useful
    when we are manipulating data regarding the users.
    """
    
    @jwt_required()
    def get(self):
        userid = get_jwt_identity()
        user = User.query.get(userid)
        if not user:
            return {"message": "User Not Found"}, 404
        return user_schema.dump(user), 200

    @jwt_required()
    def delete(self, userid):
        user = User.query.get(userid)
        if not user:
            return {"message": "User Not Found"}, 404
        user.delete_from_db()
        return {"message": "User deleted."}, 200


class TokenRefresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        return {"access_token": new_token}, 200
