from mm import mm
from models.user import User

class UserSchema(mm.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_only = ("password", )
        dump_only = ("id",)
        load_instance = True