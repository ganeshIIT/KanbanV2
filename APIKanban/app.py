from flask import Flask, jsonify
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from datetime import timedelta


from db import db
from blocklist import BLOCKLIST

from models import Bucket, User, Card

from resources.user import UserRegister, UserLogin, UserApi, TokenRefresh, UserLogout
from resources.bucket import BucketApi, BucketList
from resources.card import CardApi, CardList
from resources.summary import SummaryApi, UserData, SendEmail, DataExport, ListsExport, CardsExport

from mm import mm
from caching import cache
from celeryconfig import make_celery
import workers


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PROPAGATE_EXCEPTIONS"] = True
app.config["JWT_SECRET_KEY"] = "my secret key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
db.init_app(app)
mm.init_app(app)
CORS(app)

api = Api(app)
jwt = JWTManager(app)

cache.init_app(app, config={
    'CACHE_TYPE' : 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT' : 1000,
    'CACHE_KEY_PREFIX' : 'task_api',
    'CACHE_REDIS_URL' : 'redis://localhost:6379/1',
})

celery = workers.celery

celery.conf.broker_url = 'redis://localhost:6379/2'
celery.conf.result_backend = 'redis://localhost:6379/2'
celery.conf.timezone = 'Asia/Calcutta'
celery.conf.enable_utc = False
# celery.conf.update(
#     CELERY_BROKER_URL='redis://localhost:6379/2',
#     CELERY_RESULT_BACKEND='redis://localhost:6379/3'
# )
celery.Task = workers.ContextTask

app.app_context().push()
    
@app.before_first_request
def create_tables():
    db.create_all()


@jwt.additional_claims_loader
def add_claims_to_jwt(identity):
    # TODO: Read from a config file instead of hard-coding
    if identity == 1:
        return {"is_admin": True}
    return {"is_admin": False}


@jwt.token_in_blocklist_loader
def check_if_token_in_blocklist(jwt_header, jwt_payload):
    return jwt_payload["jti"] in BLOCKLIST


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"message": "The token has expired.", "error": "token_expired"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return (
        jsonify(
            {"message": "Signature verification failed.", "error": "invalid_token"}
        ),
        401,
    )


@jwt.unauthorized_loader
def missing_token_callback(error):
    return (
        jsonify(
            {
                "description": "Request does not contain an access token.",
                "error": "authorization_required",
            }
        ),
        401,
    )


@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    return (
        jsonify(
            {"description": "The token is not fresh.", "error": "fresh_token_required"}
        ),
        401,
    )


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return (
        jsonify(
            {"description": "The token has been revoked.", "error": "token_revoked"}
        ),
        401,
    )


api.add_resource(UserRegister, "/register")
api.add_resource(UserLogin, "/login")
api.add_resource(UserLogout, "/logout")
api.add_resource(UserApi, "/user")
api.add_resource(TokenRefresh, "/refresh")
api.add_resource(BucketApi, "/list/<int:bucketid>")
api.add_resource(BucketList, "/lists")
api.add_resource(CardApi, "/card/<int:bucketid>/<int:cardid>")
api.add_resource(CardList, "/cards/<int:bucketid>")
api.add_resource(SummaryApi, "/summary")
api.add_resource(UserData, "/")
api.add_resource(SendEmail, "/email")
api.add_resource(DataExport, "/data")
api.add_resource(ListsExport, "/listdata")
api.add_resource(CardsExport, "/carddata/<int:bucketid>")


print("Everything was successful!!!")


if __name__ == '__main__': 
    app.run(port=6060, debug=True)