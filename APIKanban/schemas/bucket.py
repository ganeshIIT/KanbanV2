from mm import mm
from models.bucket import Bucket
from .card import CardSchema

class BucketSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = Bucket
        # load_only = ("user", )
        dump_only = ("id","userid")
        include_fk = True
        load_instance = True
    cards = mm.Nested(CardSchema, many=True)