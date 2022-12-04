from db import db

class Bucket(db.Model):
    __tablename__ = 'buckets'
    id = db.Column(db.Integer(), primary_key = True)
    bucketname = db.Column(db.String(length = 128), nullable = False)
    # Foreign key refers the users table
    userid = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable = False)
    
    user = db.relationship("User", back_populates="buckets")
    # Gets the bucket of the card
    #cards = db.relationship('Card', backref='cardbucket', lazy=True)
    cards = db.relationship('Card', back_populates="bucket", lazy="dynamic")
    
    __table_args__ = (db.UniqueConstraint(bucketname, userid),)
    
    
    def json(self):
        return {
        "id": self.id,
        "bucketname": self.bucketname,
        "cards": [card.json() for card in self.cards.all()]
    }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()
    
    def __repr__(self) -> str:
        return f'Bucket {self.bucketname}'
    
    
