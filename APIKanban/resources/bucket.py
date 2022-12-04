from flask import request, jsonify
from flask_restful import Resource,reqparse, fields, marshal_with
from sqlalchemy.exc import SQLAlchemyError
from models import Bucket, Card

from marshmallow import ValidationError

from schemas.bucket import BucketSchema

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

_bucket_parser = reqparse.RequestParser()
_bucket_parser.add_argument(
    "name", type=str, required=True, help="This field cannot be blank."
)

bucketschema = BucketSchema()

class BucketApi(Resource):
    @jwt_required()
    def get(self, bucketid):
        userid = get_jwt_identity()
        bucket = Bucket.query.filter_by(id = bucketid, userid=userid).first()
        if bucket:
            return bucketschema.dump(bucket), 200
        return {"message": "List not found"}, 404
    
    @jwt_required()
    def delete(self, bucketid):
        userid = get_jwt_identity()
        bucket = Bucket.query.filter_by(id = bucketid, userid=userid).first()
        if bucket:
            Card.query.filter_by(bucketid = bucketid).delete()
            bucket.delete_from_db()
            return {"message": "List deleted"}, 200
        return {"message": "List not found"}, 404
    
    @jwt_required()
    def put(self, bucketid):
        userid = get_jwt_identity()
        # data = _bucket_parser.parse_args()
        bucket_json = request.get_json()
        bucket = Bucket.query.filter_by(id = bucketid, userid=userid).first()
        if bucket:
            bucket.bucketname =bucket_json["bucketname"]
            bucket.save_to_db()
            return {"message": "List updated"}, 200
        return {"message": "List not found"}, 404

    
class BucketList(Resource):
    @jwt_required()
    def get(self):
        userid = get_jwt_identity()
        return [bucketschema.dump(bucket) for bucket in Bucket.query.filter_by(userid = userid)], 200
    
    @jwt_required()
    def post(self):
        userid = get_jwt_identity()
        # data = _bucket_parser.parse_args()
        
        bucket = bucketschema.load(request.get_json())
        bucket.userid = userid
        
        if Bucket.query.filter_by(bucketname =bucket.bucketname, userid=userid).first():
            return {
                "message": "A List with name '{}' already exists.".format(bucket.bucketname)
            }, 400

        # bucket = Bucket(bucketname=bucket.bucketname, userid=userid)
        try:
            bucket.save_to_db()
        except SQLAlchemyError:
            return {"message": "An error occurred creating the List."}, 500

        return bucket.json(), 201

    
