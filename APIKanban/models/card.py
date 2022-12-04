from db import db
from datetime import datetime
from . import Bucket, User

class Card(db.Model):
    __tablename__ = 'cards'
    id = db.Column(db.Integer, primary_key = True)
    cardtitle = db.Column(db.String(length = 128), nullable = False)
    content = db.Column(db.Text, nullable = False)
    deadline = db.Column(db.DateTime, nullable = False)
    iscompleted = db.Column(db.Boolean, nullable = False)
    # Foreign key refers the buckets table
    bucketid = db.Column(db.Integer, db.ForeignKey('buckets.id'))
    completeddate = db.Column(db.DateTime, nullable=True)
    
    insertdate = db.Column(db.DateTime, nullable = False)
    updatedate = db.Column(db.DateTime, nullable = False, default=datetime.now)
    
    bucket = db.relationship("Bucket", back_populates="cards")
    
    __table_args__ = (db.UniqueConstraint(cardtitle, bucketid),)
    
    
    def json(self):
        return {
        "id": self.id,
        "cardtitle": self.cardtitle,
        "deadline":self.deadline.strftime('%Y-%m-%d'),
        "iscompleted":self.iscompleted,
        "content": self.content,
        "bucketid": self.bucketid,
        "completeddate":self.completeddate.strftime('%Y-%m-%d  %H:%M:%S') if self.completeddate else None,
        "insertdate":self.insertdate.strftime('%Y-%m-%d  %H:%M:%S'),
        "updatedate":self.updatedate.strftime('%Y-%m-%d  %H:%M:%S')
    }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()
    
    def __repr__(self) -> str:
        return f'Card {self.cardtitle}'