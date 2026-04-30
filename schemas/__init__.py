from marshmallow import Schema, fields, validate


class RecipeCreateSchema(Schema):
    """Schema for creating a recipe."""
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    ingredients = fields.List(fields.Str(), required=True, validate=validate.Length(min=1))
    steps = fields.List(fields.Str(), required=True, validate=validate.Length(min=1))
    cuisine_type = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    difficulty = fields.Str(
        required=True,
        validate=validate.OneOf(["easy", "medium", "hard"])
    )
    prep_time_minutes = fields.Int(required=True, validate=validate.Range(min=0))
    cook_time_minutes = fields.Int(required=True, validate=validate.Range(min=0))
    servings = fields.Int(required=True, validate=validate.Range(min=1))
    image_url = fields.Str(allow_none=True)
    is_published = fields.Bool(dump_default=False)


class RecipeUpdateSchema(Schema):
    """Schema for updating a recipe."""
    title = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(validate=validate.Length(min=1))
    ingredients = fields.List(fields.Str(), validate=validate.Length(min=1))
    steps = fields.List(fields.Str(), validate=validate.Length(min=1))
    cuisine_type = fields.Str(validate=validate.Length(min=1, max=100))
    difficulty = fields.Str(validate=validate.OneOf(["easy", "medium", "hard"]))
    prep_time_minutes = fields.Int(validate=validate.Range(min=0))
    cook_time_minutes = fields.Int(validate=validate.Range(min=0))
    servings = fields.Int(validate=validate.Range(min=1))
    image_url = fields.Str(allow_none=True)
    is_published = fields.Bool()
