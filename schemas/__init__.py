from marshmallow import Schema, fields, validate


class RecipeCreateSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    ingredients = fields.List(fields.Str(), required=True, validate=validate.Length(min=1))
    steps = fields.List(fields.Str(), required=True, validate=validate.Length(min=1))
    cuisine_type = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    cook_time_minutes = fields.Int(required=True, validate=validate.Range(min=0))
    servings = fields.Int(required=True, validate=validate.Range(min=1))
    is_published = fields.Bool(load_default=False)
    favorites_count = fields.Int(dump_only=True, load_default=0)  # read-only, set by DB

class RecipeUpdateSchema(Schema):
    title = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(validate=validate.Length(min=1))
    ingredients = fields.List(fields.Str(), validate=validate.Length(min=1))
    steps = fields.List(fields.Str(), validate=validate.Length(min=1))
    cuisine_type = fields.Str(validate=validate.Length(min=1, max=100))
    cook_time_minutes = fields.Int(validate=validate.Range(min=0))
    servings = fields.Int(validate=validate.Range(min=1))
    is_published = fields.Bool()


class ProfileSchema(Schema):
    id         = fields.UUID(dump_only=True)
    email      = fields.Email(required=False)
    name       = fields.Str(required=False, validate=validate.Length(min=1, max=100))
    avatar_url = fields.Url(required=False, load_default=None)
    created_at = fields.DateTime(dump_only=True)

class ProfileUpdateSchema(Schema):
    name       = fields.Str(validate=validate.Length(min=1, max=100))
    avatar_url = fields.Url()