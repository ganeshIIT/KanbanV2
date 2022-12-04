from mm import mm
from models.card import Card
from models.bucket import Bucket

class CardSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = Card
        load_only = ("bucket", )
        dump_only = ("id","bucketid")
        include_fk = True
        include_uk = True
        load_instance = True