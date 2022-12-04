from db import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer(), primary_key = True)
    username = db.Column(db.String(length = 30), nullable = False, unique = True)
    email = db.Column(db.String(length = 128), nullable = True, unique = True)
    password = db.Column(db.String(length = 255), nullable = False)
    # Gets the user of the bucket
    buckets = db.relationship('Bucket', back_populates="user", lazy="dynamic")
    
    # buckets = db.relationship('Bucket', backref='bucketuser', lazy=True)
    
    # def check_password(self, password):
    #     return self.password == password 
    
    # def json(self):
    #     return {
    #     'id': self.id,
    #     'username': self.username,
    #     'email': self.email,
    #     "buckets": [bucket.json() for bucket in self.buckets.all()]
    # }

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self):
        db.session.delete(self)
        db.session.commit()
    