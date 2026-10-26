from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(min=3, max=30))
    password = fields.Str(
        load_only=True,
        required=True,
        validate=validate.Length(min=8, max=128),
    )


class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class NoteSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    category = fields.Str(load_default="general", validate=validate.Length(min=1, max=30))
    created_at = fields.DateTime(dump_only=True)
    user_id = fields.Int(dump_only=True)


user_schema = UserSchema()
login_schema = LoginSchema()
note_schema = NoteSchema()
notes_schema = NoteSchema(many=True)
note_update_schema = NoteSchema(partial=True)