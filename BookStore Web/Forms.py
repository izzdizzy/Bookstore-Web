from flask_wtf import FlaskForm  # Use FlaskForm instead of Form
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, validators, FileField, IntegerField, TextAreaField, Form
from wtforms.fields.choices import SelectField
from wtforms.fields.datetime import DateField
from wtforms.fields.numeric import FloatField
from wtforms.fields.simple import PasswordField, BooleanField


class CreateCardForm(Form):  # Inherit from FlaskForm
    first_name = StringField('First Name', [validators.Length(min=1, max=150), validators.DataRequired()])
    last_name = StringField('Last Name', [validators.Length(min=1, max=150), validators.DataRequired()])
    card_number = StringField('Card_Number', [validators.DataRequired(), validators.Length(min=16, max=16)])
    expiry_date = DateField('Expiry Date', [validators.DataRequired()], format='%Y-%m-%d')
    cvc_number = StringField('CVC', [validators.DataRequired(), validators.Length(min=3, max=3)])

class CreateEbookForm(Form):  # Inherit from FlaskForm
    title = StringField('Title', [validators.Length(min=1, max=200), validators.DataRequired()])
    author = StringField('Author', [validators.Length(min=1, max=150), validators.DataRequired()])
    description = TextAreaField('Description', [validators.Optional()])
    price = FloatField('Price', [validators.DataRequired(), validators.NumberRange(min=0)])
    genre = StringField('Genre', [validators.Length(min=1, max=100), validators.DataRequired()])
    image = FileField('Ebook Cover Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    content = FileField('Ebook Content (PDF)', validators=[FileAllowed(['pdf'], 'PDF files only!')])


class CreateUserForm(Form):  # Inherit from FlaskForm
    username = StringField('Username', [validators.Length(min=1, max=150), validators.DataRequired()])
    email = StringField('Email', [validators.Email(), validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])
    role = SelectField('Role', [validators.DataRequired()], choices=[('User', 'User'), ('Staff', 'Staff')],
                       default='User')

class CreateReviewForm(FlaskForm):
    stars = IntegerField('Stars', [validators.NumberRange(min=1, max=5), validators.DataRequired()])
    comment = TextAreaField('Comment', [validators.Length(max=500), validators.DataRequired()])
    anonymous = BooleanField('Post Anonymously')