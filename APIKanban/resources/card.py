from flask import request, abort
from flask_restful import Resource, reqparse
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from marshmallow import ValidationError

from schemas.card import CardSchema

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_jwt,
    jwt_required,
)
from models import Card, Bucket

cardschema = CardSchema()

class CardApi(Resource):
    
    @jwt_required()
    def get(self, bucketid, cardid):
        userid = get_jwt_identity()
        bucket = Bucket.query.filter_by(id = bucketid, userid=userid).first()
        if not bucket:
            raise abort(404, "Bucket not found")
        card = Card.query.filter_by(id = cardid, bucketid = bucket.id).first()
        if card:
            return cardschema.dump(card)
        return {"message":"Card not found"}, 404
    
    @jwt_required()
    def put(self, bucketid, cardid):
        # data = request.json
        card_json = request.get_json()
        userid = get_jwt_identity()
        bucket = Bucket.query.filter_by(id = bucketid, userid=userid).first()
        if not bucket:
            return {"message": "Bucket not found"}, 404
        # if Card.query.filter_by(cardtitle =card_json["cardtitle"], bucketid = bucket.id).first():
        #     return {"message": "A Card with title '{}' already exists.".format(card_json["cardtitle"])}, 400
            
        card = Card.query.filter_by(id = cardid, bucketid = bucket.id).first()
        if not card:
            return {"message": "Card not found"}, 404
        
        # card = cardschema.load(card_json)
        
        completeddate = card.completeddate
        if (card_json["iscompleted"] and not card.completeddate):
            completeddate = datetime.now()
        if (not card_json["iscompleted"] and card.completeddate):
            completeddate = None
        
        if card:
            card.cardtitle = card_json['cardtitle']
            card.content= card_json['content'] 
            card.deadline= datetime.strptime(card_json['deadline'].split('T')[0], '%Y-%m-%d').date()
            card.iscompleted= card_json['iscompleted']
            card.completeddate= completeddate
            card.updatedate= datetime.now()
            card.bucketid = bucket.id
            card.save_to_db()
            return cardschema.dump(card)
            
        return {"message": "Card not found"}, 404
    
    @jwt_required()
    def delete(self, bucketid, cardid):
        userid = get_jwt_identity()
        bucket = Bucket.query.filter_by(id = bucketid, userid=userid).first()
        card = Card.query.filter_by(id = cardid, bucketid = bucket.id).first()
        if card:
            card.delete_from_db()
            return {"message": "Card Deleted"}, 200
        return {"message": "Card not found"}, 404
    
    
class CardList(Resource):
    @jwt_required()
    def get(self, bucketid):
        userid = get_jwt_identity()
        bucket = Bucket.query.filter_by(id = bucketid, userid=userid).first()
        return [cardschema.dump(card) for card in Card.query.filter_by(bucketid = bucket.id)]
    
    @jwt_required()
    def post(self, bucketid):
        card_json = request.get_json()
        userid = get_jwt_identity()
        bucket = Bucket.query.filter_by(id = bucketid, userid=userid).first()
        
        if Card.query.filter_by(cardtitle =card_json["cardtitle"], bucketid = bucket.id).first():
             return {"message": "A Card with title '{}' already exists.".format(card_json["cardtitle"])}, 400
        
        newCard = Card(cardtitle = card_json['cardtitle'], 
                        content= card_json['content'], 
                        deadline= datetime.strptime(card_json['deadline'], '%Y-%m-%d').date(),
                        iscompleted= card_json['iscompleted'], 
                        completeddate= datetime.now() if card_json['iscompleted'] else None, 
                        insertdate= datetime.now(), 
                       bucketid = bucket.id
                       )
        try:
            newCard.save_to_db()
        except SQLAlchemyError:
            return {"message": "An error occurred creating the Card."}, 500

        return cardschema.dump(newCard), 201