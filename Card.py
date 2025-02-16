from datetime import datetime

# Card.py are where all classes are stored, renaming it causes it to not work and i dont really know why


class Card:
    count_id = 0  # Class variable to track the last used ID

    def __init__(self, first_name, last_name, card_number, expiry_date, cvc_number, user_id=None, card_id=None):
        # If card_id is not provided, generate a new one
        if card_id is None:
            Card.count_id += 1
            self.__card_id = Card.count_id
        else:
            self.__card_id = card_id
            # Update count_id if the provided card_id is greater
            if card_id > Card.count_id:
                Card.count_id = card_id

        # Add user_id to associate the card with a specific user
        self.__user_id = user_id
        self.__first_name = first_name
        self.__last_name = last_name
        self.__card_number = card_number
        self.__expiry_date = expiry_date
        self.__cvc_number = cvc_number

    # Getters and setters for user_id
    def get_user_id(self):
        return self.__user_id

    def set_user_id(self, user_id):
        self.__user_id = user_id

    # Existing getters and setters
    def get_first_name(self):
        return self.__first_name

    def get_last_name(self):
        return self.__last_name

    def get_card_id(self):
        return self.__card_id

    def get_card_number(self):
        return self.__card_number

    def get_expiry_date(self):
        return self.__expiry_date

    def get_cvc_number(self):
        return self.__cvc_number

    def set_card_id(self, card_id):
        self.__card_id = card_id

    def set_first_name(self, first_name):
        self.__first_name = first_name

    def set_last_name(self, last_name):
        self.__last_name = last_name

    def set_card_number(self, card_number):
        self.__card_number = card_number

    def set_expiry_date(self, expiry_date):
        self.__expiry_date = expiry_date

    def set_cvc_number(self, cvc_number):
        self.__cvc_number = cvc_number

class Ebook:
    count_id = 0

    def __init__(self, title, author, description, price, genre, image, content_path=None, ebook_id=None):
        if ebook_id is None:
            Ebook.count_id += 1
            self.__ebook_id = Ebook.count_id
        else:
            self.__ebook_id = ebook_id
            if ebook_id > Ebook.count_id:
                Ebook.count_id = ebook_id

        self.__title = title
        self.__author = author
        self.__description = description
        self.__price = price
        self.__genre = genre
        self.__image = image
        self.__content_path = content_path
        self.average_rating = 0  # Default average rating
        self.total_reviews = 0  # Default total reviews

    # Getters and setters
    def get_ebook_id(self):
        return self.__ebook_id

    def get_title(self):
        return self.__title

    def get_author(self):
        return self.__author

    def get_description(self):
        return self.__description

    def get_price(self):
        return self.__price

    def get_genre(self):
        return self.__genre

    def get_image(self):
        return self.__image

    def get_content_path(self):
        return self.__content_path

    def set_average_rating(self, average_rating):
        self.average_rating = average_rating

    def set_total_reviews(self, total_reviews):
        self.total_reviews = total_reviews

    def set_ebook_id(self, ebook_id):
        self.__ebook_id = ebook_id

    def set_title(self, title):
        self.__title = title

    def set_author(self, author):
        self.__author = author

    def set_description(self, description):
        self.__description = description

    def set_price(self, price):
        self.__price = price

    def set_genre(self, genre):
        self.__genre = genre

    def set_content_path(self, content_path):
        self.__content_path = content_path

    def set_image(self, image):
        self.__image = image

class User:
    count_id = 0

    def __init__(self, username, email, password, role='User'):
        User.count_id += 1
        self.__user_id = User.count_id
        self.__username = username
        self.__email = email
        self.__password = password
        self.__role = role  # Role can be 'Owner', 'Co-owner', 'Staff', or 'User'

    def get_user_id(self):
        return self.__user_id

    def get_username(self):
        return self.__username

    def get_email(self):
        return self.__email

    def get_password(self):
        return self.__password

    def get_role(self):
        return self.__role

    def set_username(self, username):
        self.__username = username

    def set_email(self, email):
        self.__email = email

    def set_password(self, password):
        self.__password = password

    def set_role(self, role):
        self.__role = role




class Transaction:
    count_id = 0  # Class variable to generate unique transaction IDs

    def __init__(self, user_id, username, title, amount_paid, transaction_id=None):
        if transaction_id is None:
            Transaction.count_id += 1
            self.__transaction_id = Transaction.count_id
        else:
            self.__transaction_id = transaction_id
            if transaction_id > Transaction.count_id:
                Transaction.count_id = transaction_id

        self.__user_id = user_id
        self.__username = username
        self.__title = title
        self.__amount_paid = amount_paid
        self.__timestamp = datetime.now()  # Record the time of the transaction
        self.__refund_status = "Not Refunded"  # Default refund status

    # Getters
    def get_transaction_id(self):
        return self.__transaction_id

    def get_user_id(self):
        return self.__user_id

    def get_username(self):
        return self.__username

    def get_title(self):
        return self.__title

    def get_amount_paid(self):
        return self.__amount_paid

    def get_timestamp(self):
        return self.__timestamp

    def get_refund_status(self):
        return self.__refund_status

    # Setters
    def set_user_id(self, user_id):
        self.__user_id = user_id

    def set_username(self, username):
        self.__username = username

    def set_title(self, title):
        self.__title = title

    def set_amount_paid(self, amount_paid):
        self.__amount_paid = amount_paid

    def set_refund_status(self, refund_status):
        self.__refund_status = refund_status

class Review:
    count_id = 0

    def __init__(self, user_id, username, ebook_id, stars, comment, anonymous=False, review_id=None):
        if review_id is None:
            Review.count_id += 1
            self.__review_id = Review.count_id
        else:
            self.__review_id = review_id
            if review_id > Review.count_id:
                Review.count_id = review_id
        self.__user_id = user_id
        self.__username = username if not anonymous else 'Anonymous'
        self.__ebook_id = ebook_id
        self.__stars = stars
        self.__comment = comment
        self.__anonymous = anonymous
        self.__timestamp = datetime.now()

    def get_review_id(self):
        return self.__review_id

    def get_user_id(self):
        return self.__user_id

    def get_username(self):
        return self.__username

    def get_ebook_id(self):
        return self.__ebook_id

    def get_stars(self):
        return self.__stars

    def get_comment(self):
        return self.__comment

    def get_anonymous(self):
        return self.__anonymous

    def get_timestamp(self):
        return self.__timestamp

    def set_stars(self, stars):
        self.__stars = stars

    def set_comment(self, comment):
        self.__comment = comment

    def set_anonymous(self, anonymous, username):
        self.__anonymous = anonymous
        self.__username = 'Anonymous' if anonymous else username