import random
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from Forms import CreateCardForm, CreateEbookForm, CreateReviewForm
from datetime import datetime
import shelve, Card
import re
from werkzeug.utils import secure_filename
from Card import Card, Ebook, User, Review, Transaction

# Define the upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
ALLOWED_EXTENSIONS = {'jpg', 'png', 'jpeg'}

app = Flask(__name__)
app.secret_key = 'secret_key'

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

with shelve.open('user.db', writeback=True) as db:
    if 'Users' not in db:
        db['Users'] = {}

    # Check if a default owner account exists
    default_owner_username = "owner"  # Change this to your desired default username
    default_owner_exists = any(user.get_username() == default_owner_username for user in db['Users'].values())

    if not default_owner_exists:
        # Create a default owner account
        default_owner = User(
            username=default_owner_username,
            email="owner@example.com",
            password="owner123",
            role="Owner"
        )
        db['Users'][default_owner.get_user_id()] = default_owner
        print("Default owner account created.")

    # Convert keys to integers (if necessary)
    db['Users'] = {int(k): v for k, v in db['Users'].items()}
    User.count_id = max(db['Users'].keys(), default=0)


def staff_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] not in ['Staff', 'Owner', 'Co-owner']:
            flash('Access denied. Staff or Owner only.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/staff')
@staff_only  # Ensure only staff (owners/co-owners) can access this route
def staff():
    if 'role' not in session or session['role'] not in ['Staff', 'Owner', 'Co-owner']:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))

    # Pass the user's role to the template
    role = session.get('role', 'User')
    return render_template('staff.html', role=role)

@app.route('/')
def home():
    # Open the ebooks database (create if it doesn't exist)
    ebooks_dict = {}
    try:
        db = shelve.open('ebooks.db', 'c')
        try:
            # Try to retrieve the 'Ebooks' dictionary
            ebooks_dict = db.get('Ebooks', {})  # Use .get() to avoid KeyError
            if not ebooks_dict:  # If 'Ebooks' key doesn't exist or is empty
                db['Ebooks'] = {}  # Initialize an empty dictionary
                ebooks_dict = db['Ebooks']
        except Exception as e:
            print(f"Error accessing ebooks.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening ebooks.db: {e}")

    # Open the reviews database (create if it doesn't exist)
    reviews_dict = {}
    is_empty = True  # Assume there are no reviews by default
    try:
        db = shelve.open('reviews.db', 'c')
        try:
            # Try to retrieve the 'Reviews' dictionary
            reviews_dict = db.get('Reviews', {})  # Use .get() to avoid KeyError
            if not reviews_dict:  # If 'Reviews' key doesn't exist or is empty
                db['Reviews'] = {}  # Initialize an empty dictionary
                reviews_dict = db['Reviews']
            is_empty = len(reviews_dict) == 0  # Check if the reviews database is empty
        except Exception as e:
            print(f"Error accessing reviews.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening reviews.db: {e}")

    # Convert the dictionary values to a list
    ebooks_list = list(ebooks_dict.values())

    # Calculate average rating and total reviews for each book
    for ebook in ebooks_list:
        book_reviews = [review for review in reviews_dict.values() if review.get_ebook_id() == ebook.get_ebook_id()]
        total_reviews = len(book_reviews)
        if total_reviews > 0:
            average_rating = sum(review.get_stars() for review in book_reviews) / total_reviews
        else:
            average_rating = 0
        # Add the average rating and total reviews to the ebook object
        ebook.average_rating = average_rating
        ebook.total_reviews = total_reviews

    # Featured Books: Top 6 books with the highest average ratings
    featured_books = sorted(ebooks_list, key=lambda x: x.average_rating, reverse=True)[:6]

    # Random Genre Books: Select a random genre and get 6 books from that genre
    genres = set(ebook.get_genre() for ebook in ebooks_list)
    random_genre = random.choice(list(genres)) if genres else None
    random_genre_books = [ebook for ebook in ebooks_list if ebook.get_genre() == random_genre][:6]

    # Check if the user owns each ebook
    if 'user_id' in session:
        user_id = session['user_id']
        try:
            inventory_db = shelve.open('inventory.db', 'r')
            inventory_dict = inventory_db.get('Inventory', {})
            user_inventory = inventory_dict.get(user_id, [])
            inventory_db.close()
        except Exception as e:
            print(f"Error accessing inventory.db: {e}")
            user_inventory = []
    else:
        user_inventory = []

    for ebook in featured_books + random_genre_books:
        ebook.is_owned = ebook.get_ebook_id() in user_inventory

    return render_template('home.html', featured_books=featured_books, random_genre_books=random_genre_books, random_genre=random_genre, is_empty=is_empty)


@app.route('/promote_user/<int:user_id>/<role>', methods=['POST'])
@staff_only  # Ensure only staff (owners/co-owners) can access this route
def promote_user(user_id, role):
    if 'role' not in session or session['role'] not in ['Owner', 'Co-owner']:
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('user_management'))

    with shelve.open('user.db', writeback=True) as db:
        users_dict = db['Users']
        if user_id not in users_dict:
            flash('User not found.', 'error')
            return redirect(url_for('user_management'))

        target_user = users_dict[user_id]
        current_user_role = session['role']

        # Role hierarchy rules
        if current_user_role == 'Owner':
            if role in ['Owner', 'Co-owner', 'Staff', 'User']:
                target_user.set_role(role)
                flash(f'User {target_user.get_username()} has been promoted to {role}.', 'success')
            else:
                flash('Invalid role.', 'error')
        elif current_user_role == 'Co-owner':
            if role in ['Staff', 'User']:
                target_user.set_role(role)
                flash(f'User {target_user.get_username()} has been promoted to {role}.', 'success')
            else:
                flash('You do not have permission to promote to this role.', 'error')
        else:
            flash('You do not have permission to perform this action.', 'error')

        db['Users'] = users_dict

    return redirect(url_for('user_management'))

@app.route('/promote_to_staff/<int:user_id>', methods=['POST'])
@staff_only
def promote_to_staff(user_id):
    with shelve.open('user.db', writeback=True) as db:
        users_dict = db['Users']
        if user_id in users_dict:
            user = users_dict[user_id]
            user.set_role('Staff')
            db['Users'] = users_dict
            flash(f'User {user.get_username()} has been promoted to Staff.', 'success')
        else:
            flash('User not found.', 'error')

    return redirect(url_for('user_management'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        repeat_password = request.form['repeat_password']
        role = request.form.get('role', 'User')  # Default to 'User' if role is not provided

        # Ensure only Owners and Co-owners can create Staff or Co-owner accounts
        if role in ['Staff', 'Co-owner'] and ('role' not in session or session['role'] not in ['Owner', 'Co-owner']):
            flash('You do not have permission to create this type of account.', 'error')
            return redirect(url_for('register'))

        if password != repeat_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))

        with shelve.open('user.db', writeback=True) as db:
            users_dict = db.get('Users', {})

            # Check for duplicate usernames
            if any(user.get_username() == username for user in users_dict.values()):
                flash('This username already exists.', 'error')
                return redirect(url_for('register'))

            # Create and save the new user
            user = User(username, email, password, role)
            users_dict[user.get_user_id()] = user
            db['Users'] = users_dict

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with shelve.open('user.db') as db:
            users_dict = db['Users']
            for user in users_dict.values():
                if user.get_username() == username and user.get_password() == password:
                    session['user_id'] = user.get_user_id()
                    session['username'] = user.get_username()  # Store username in session
                    session['role'] = user.get_role()
                    return redirect(url_for('home'))

        flash('Invalid credentials, please try again.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/user_management')
@staff_only
def user_management():
    if 'user_id' not in session or session.get('role') not in ['Staff', 'Owner', 'Co-owner']:
        flash('Access denied. Staff or Owner only.', 'error')
        return redirect(url_for('login'))

    # Retrieve filter parameters from request
    filter_user_id = request.args.get('user_id', type=int)
    filter_username = request.args.get('username', '').strip().lower()
    filter_email = request.args.get('email', '').strip().lower()
    filter_role = request.args.get('role', '').strip().lower()

    with shelve.open('user.db') as db:
        users_dict = db.get('Users', {})
        users = list(users_dict.values())

    # Apply filters
    if filter_user_id:
        users = [user for user in users if user.get_user_id() == filter_user_id]
    if filter_username:
        users = [user for user in users if filter_username in user.get_username().lower()]
    if filter_email:
        users = [user for user in users if filter_email in user.get_email().lower()]
    if filter_role:
        users = [user for user in users if filter_role == user.get_role().lower()]

    return render_template(
        'user_management.html',
        users=users,
        filter_user_id=filter_user_id,
        filter_username=filter_username,
        filter_email=filter_email,
        filter_role=filter_role
    )


@app.route('/create_user', methods=['GET', 'POST'])
@staff_only
def create_user():
    if 'user_id' not in session or session.get('role') not in ['Staff', 'Owner', 'Co-owner']:
        flash('Access denied. Staff or Owner only.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        with shelve.open('user.db', writeback=True) as db:
            users_dict = db['Users']

            if any(user.get_username() == username for user in users_dict.values()):
                flash('This username already exists.', 'error')
                return redirect(url_for('user_management'))

            user = User(username=username, email=email, password=password, role=role)
            users_dict[user.get_user_id()] = user
            db['Users'] = users_dict

        flash('User created successfully!', 'success')
        return redirect(url_for('user_management'))

    return render_template('create_user.html')

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@staff_only
def delete_user(user_id):
    if 'role' not in session or session['role'] not in ['Staff', 'Owner', 'Co-owner']:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))

    with shelve.open('user.db', writeback=True) as db:
        users_dict = db['Users']
        if user_id in users_dict:
            del users_dict[user_id]
            db['Users'] = users_dict
            flash('User deleted successfully!', 'success')
        else:
            flash('User not found.', 'error')

    return redirect(url_for('user_management'))

@app.route('/update_user/<int:user_id>', methods=['GET', 'POST'])
@staff_only
def update_user(user_id):
    # Ensure only 'Owner' role can access this functionality
    if 'role' not in session or session['role'] not in ['Owner', 'Co-owner']:
        flash('Access denied!', 'error')
        return redirect(url_for('user_management'))

    with shelve.open('user.db', writeback=True) as db:
        users_dict = db.get('Users', {})
        if user_id not in users_dict:
            flash('User not found.', 'error')
            return redirect(url_for('user_management'))

        user = users_dict[user_id]
        if request.method == 'POST':
            # Check for duplicate username
            new_username = request.form['username']
            if any(existing_user.get_username() == new_username and existing_id != user_id
                   for existing_id, existing_user in users_dict.items()):
                flash('This username already exists.', 'error')
                return redirect(url_for('user_management', user_id=user_id))

            # Update user details
            user.set_username(new_username)
            user.set_email(request.form['email'])
            if request.form['password']:  # Only update password if provided
                user.set_password(request.form['password'])
            user.set_role(request.form['role'])
            users_dict[user_id] = user
            db['Users'] = users_dict

            flash('User updated successfully.', 'success')
            return redirect(url_for('user_management'))

        return render_template('update_user.html', user=user, user_id=user_id)

# Function to check if a file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')


@app.route('/reviews/<int:id>', methods=['GET', 'POST'])
def reviews(id):
    if 'user_id' not in session:
        flash('You need to log in to view reviews.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username', 'Unknown User')

    create_review_form = CreateReviewForm(request.form)

    # Open the ebooks database to get the ebook details
    db = shelve.open('ebooks.db', 'r')
    ebooks_dict = db['Ebooks']
    db.close()
    ebook = ebooks_dict.get(id)

    if not ebook:
        flash('Ebook not found.', 'error')
        return redirect(url_for('store'))

    # Open the reviews database (create if it doesn't exist)
    reviews_dict = {}
    try:
        db = shelve.open('reviews.db', 'c')
        try:
            reviews_dict = db.get('Reviews', {})
            if not reviews_dict:
                db['Reviews'] = {}
                reviews_dict = db['Reviews']
        except Exception as e:
            print(f"Error accessing reviews.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening reviews.db: {e}")

    # Filter reviews for the current ebook
    book_reviews = [review for review in reviews_dict.values() if review.get_ebook_id() == id]

    # Check if the user has already reviewed this ebook
    user_review = next((review for review in book_reviews if review.get_user_id() == user_id), None)

    # Open the inventory database to check if the user owns the ebook
    user_owns_ebook = False
    try:
        inventory_db = shelve.open('inventory.db', 'r')
        inventory_dict = inventory_db.get('Inventory', {})
        user_inventory = inventory_dict.get(user_id, [])
        user_owns_ebook = id in user_inventory
        inventory_db.close()
    except Exception as e:
        print(f"Error accessing inventory.db: {e}")

    if request.method == 'POST' and create_review_form.validate():
        if not user_owns_ebook:
            flash('You must own the ebook to leave a review.', 'error')
            return redirect(url_for('reviews', id=id))

        stars = create_review_form.stars.data
        comment = create_review_form.comment.data
        anonymous = create_review_form.anonymous.data

        if user_review:
            # Update the existing review
            user_review.set_stars(stars)
            user_review.set_comment(comment)
            user_review.set_anonymous(anonymous, username)  # Pass the username here
            flash('Review updated successfully!', 'success')
        else:
            # Create a new review
            review = Review(user_id, username, id, stars, comment, anonymous)
            reviews_dict[review.get_review_id()] = review
            flash('Review submitted successfully!', 'success')

        # Save the reviews to the database
        db = shelve.open('reviews.db', 'c')
        try:
            db['Reviews'] = reviews_dict
        except Exception as e:
            print(f"Error saving review: {e}")
        finally:
            db.close()

        return redirect(url_for('reviews', id=id))

    # Calculate average rating and total reviews for the ebook
    total_reviews = len(book_reviews)
    if total_reviews > 0:
        average_rating = sum(review.get_stars() for review in book_reviews) / total_reviews
    else:
        average_rating = 0

    # Add the average rating and total reviews to the ebook object
    ebook.average_rating = average_rating
    ebook.total_reviews = total_reviews

    return render_template('reviews.html', ebook=ebook, reviews=book_reviews, form=create_review_form,
                           user_review=user_review, user_owns_ebook=user_owns_ebook)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    username = session.get('username', 'Unknown User')  # Get the username from the session

    # Fetch saved cards for the user
    saved_cards = []
    try:
        # Open the card database with error handling
        db = shelve.open('card.db', 'c')  # Use 'c' to create the database if it doesn't exist
        try:
            # Try to retrieve the 'Cards' dictionary
            cards_dict = db.get('Cards', {})  # Use .get() to avoid KeyError
            if not cards_dict:  # If 'Cards' key doesn't exist or is empty
                db['Cards'] = {}  # Initialize an empty dictionary
                cards_dict = db['Cards']
            # Filter saved cards for the logged-in user
            saved_cards = [card for card in cards_dict.values() if card.get_user_id() == user_id]
        except Exception as e:
            print(f"Error accessing card.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening card.db: {e}")

    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        card_number = request.form.get('card_number')
        expiry_date_str = request.form.get('expiry_date')
        cvc = request.form.get('cvc')
        save_card = request.form.get('save_card')  # Check if the checkbox is checked

        # Validate card number
        if not re.match(r'^(4|5[1-5]|2|3)\d{15}$', card_number):
            flash(
                'Invalid card number. It must start with 4 (VISA), 2/5 (Mastercard), or 3 (American Express) and be 16 digits long.',
                'error')
            return redirect(url_for('payment'))

        # Parse and validate expiry date
        try:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid expiry date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('payment'))
        if expiry_date.year < 2025:
            flash('Expiry date must be after 2025.', 'error')
            return redirect(url_for('payment'))

        # Validate CVC
        if not re.match(r'^\d{3}$', cvc):
            flash('Invalid CVC. It must be exactly 3 digits long.', 'error')
            return redirect(url_for('payment'))

        # Process payment
        # Open the cart database
        cart_db = shelve.open('cart.db', 'r')
        cart_dict = cart_db.get('Cart', {})
        user_cart = cart_dict.get(user_id, [])
        cart_db.close()

        # Open the inventory database
        inventory_db = shelve.open('inventory.db', 'c')
        if 'Inventory' not in inventory_db:
            inventory_db['Inventory'] = {}
        inventory_dict = inventory_db['Inventory']

        # Initialize the user's inventory if it doesn't exist
        if user_id not in inventory_dict:
            inventory_dict[user_id] = []

        # Open the ebooks database to get ebook details
        db = shelve.open('ebooks.db', 'r')
        try:
            ebooks_dict = db['Ebooks']
        except KeyError:
            flash('No ebooks found in the database.', 'error')
            return redirect(url_for('cart'))
        db.close()

        # Record the transaction in the transaction history
        transaction_db = shelve.open('transactions.db', 'c')
        if 'Transactions' not in transaction_db:
            transaction_db['Transactions'] = {}
        transactions_dict = transaction_db['Transactions']

        for ebook_id in user_cart:
            if ebook_id in ebooks_dict:
                # Check if the ebook is already in the user's inventory
                if ebook_id not in inventory_dict[user_id]:
                    # Add the ebook to the user's inventory only if it's not already there
                    inventory_dict[user_id].append(ebook_id)

                    # Create a new transaction
                    transaction = Transaction(
                        user_id=user_id,
                        username=username,
                        title=ebooks_dict[ebook_id].get_title(),
                        amount_paid=ebooks_dict[ebook_id].get_price()
                    )
                    transactions_dict[transaction.get_transaction_id()] = transaction

        # Save the updated inventory and transactions
        inventory_db['Inventory'] = inventory_dict
        inventory_db.close()
        transaction_db['Transactions'] = transactions_dict
        transaction_db.close()

        # Clear the user's cart
        cart_db = shelve.open('cart.db', 'w')
        cart_dict[user_id] = []
        cart_db['Cart'] = cart_dict
        cart_db.close()

        # Save the card if the checkbox is checked
        if save_card:
            card = Card(
                first_name=first_name,
                last_name=last_name,
                card_number=card_number,
                expiry_date=expiry_date,
                cvc_number=cvc,
                user_id=user_id  # Pass the user_id here
            )
            # Open the card database
            db = shelve.open('card.db', 'c')
            if 'Cards' not in db:
                db['Cards'] = {}
            cards_dict = db['Cards']
            # Add the new card to the database
            cards_dict[card.get_card_id()] = card
            # Save the updated cards dictionary
            db['Cards'] = cards_dict
            db.close()

        return redirect(url_for('thank_you'))

    # If it's a GET request, display the payment page
    cart_db = shelve.open('cart.db', 'r')
    cart_dict = cart_db.get('Cart', {})
    user_cart = cart_dict.get(user_id, [])  # Get the user's cart
    cart_db.close()

    # Get the ebooks in the user's cart
    ebooks_list = []
    db = shelve.open('ebooks.db', 'r')
    ebooks_dict = db['Ebooks']
    for ebook_id in user_cart:
        if ebook_id in ebooks_dict:
            ebooks_list.append(ebooks_dict[ebook_id])
    db.close()

    return render_template('payment.html', ebooks_list=ebooks_list, saved_cards=saved_cards)

@app.route('/delete_from_cart/<int:id>', methods=['POST'])
def delete_from_cart(id):
    if 'user_id' not in session:
        flash('You need to log in to modify your cart.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Open the cart database
    cart_db = shelve.open('cart.db', 'w')
    if 'Cart' not in cart_db:
        cart_db['Cart'] = {}

    cart_dict = cart_db['Cart']

    # Remove the item from the user's cart
    if user_id in cart_dict and id in cart_dict[user_id]:
        cart_dict[user_id].remove(id)

    cart_db['Cart'] = cart_dict
    cart_db.close()

    return redirect(url_for('cart'))

@app.route('/add_to_cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    if 'user_id' not in session:
        flash('You need to log in to add items to your cart.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Open the ebook database to get the product details
    db = shelve.open('ebooks.db', 'r')
    ebooks_dict = db['Ebooks']
    db.close()

    # Open the cart database to add the product
    cart_db = shelve.open('cart.db', 'c')
    if 'Cart' not in cart_db:
        cart_db['Cart'] = {}

    cart_dict = cart_db['Cart']

    # Initialize the user's cart if it doesn't exist
    if user_id not in cart_dict:
        cart_dict[user_id] = []

    # Add the ebook ID to the user's cart
    if id in ebooks_dict and id not in cart_dict[user_id]:
        cart_dict[user_id].append(id)

    cart_db['Cart'] = cart_dict
    cart_db.close()

    return redirect(url_for('cart'))

@app.route('/cart', methods=['GET', 'POST'])
def cart():
    if 'user_id' not in session:
        flash('You need to log in to view your cart.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Open the cart database (create if it doesn't exist)
    cart_dict = {}
    try:
        cart_db = shelve.open('cart.db', 'c')
        try:
            # Try to retrieve the 'Cart' dictionary
            cart_dict = cart_db.get('Cart', {})  # Use .get() to avoid KeyError
            if not cart_dict:  # If 'Cart' key doesn't exist or is empty
                cart_db['Cart'] = {}  # Initialize an empty dictionary
                cart_dict = cart_db['Cart']
        except Exception as e:
            print(f"Error accessing cart.db: {e}")
        finally:
            cart_db.close()
    except Exception as e:
        print(f"An error occurred while opening cart.db: {e}")

    # Get the user's cart
    user_cart = cart_dict.get(user_id, [])
    is_empty = len(user_cart) == 0

    # Get the ebooks in the user's cart
    ebooks_list = []
    try:
        db = shelve.open('ebooks.db', 'r')
        try:
            ebooks_dict = db['Ebooks']
            for ebook_id in user_cart:
                if ebook_id in ebooks_dict:
                    ebooks_list.append(ebooks_dict[ebook_id])
        except KeyError:
            print("No ebooks found in the database.")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening ebooks.db: {e}")

    return render_template('cart.html', ebooks_list=ebooks_list, is_empty=is_empty)




@app.route("/Store")
def store():
    # Get filter parameters from the request
    selected_genre = request.args.get('genre', '')
    min_price = request.args.get('min_price', type=float, default=0.0)
    max_price = request.args.get('max_price', type=float, default=float('inf'))
    min_rating = request.args.get('min_rating', type=float, default=0.0)

    # Open the ebooks database
    ebooks_dict = {}
    db = shelve.open('ebooks.db', 'r')
    try:
        ebooks_dict = db['Ebooks']
    except KeyError:
        print("No ebooks found in the database.")
    db.close()

    # Open the reviews database (create if it doesn't exist)
    reviews_dict = {}
    is_empty = True  # Assume there are no reviews by default
    try:
        db = shelve.open('reviews.db', 'c')
        try:
            # Try to retrieve the 'Reviews' dictionary
            reviews_dict = db.get('Reviews', {})  # Use .get() to avoid KeyError
            if not reviews_dict:  # If 'Reviews' key doesn't exist or is empty
                db['Reviews'] = {}  # Initialize an empty dictionary
                reviews_dict = db['Reviews']
            is_empty = len(reviews_dict) == 0  # Check if the reviews database is empty
        except Exception as e:
            print(f"Error accessing reviews.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening reviews.db: {e}")

    # Get the user's inventory if logged in
    user_inventory = []
    if 'user_id' in session:
        user_id = session['user_id']
        try:
            inventory_db = shelve.open('inventory.db', 'r')
            inventory_dict = inventory_db.get('Inventory', {})
            user_inventory = inventory_dict.get(user_id, [])
            inventory_db.close()
        except Exception as e:
            print(f"Error accessing inventory.db: {e}")

    # Filter ebooks based on genre, price range, and minimum rating
    ebooks_list = []
    for ebook in ebooks_dict.values():
        if (not selected_genre or ebook.get_genre() == selected_genre) and \
           (min_price <= ebook.get_price() <= max_price):
            # Calculate average rating and total reviews for this book
            book_reviews = [review for review in reviews_dict.values() if review.get_ebook_id() == ebook.get_ebook_id()]
            total_reviews = len(book_reviews)
            if total_reviews > 0:
                average_rating = sum(review.get_stars() for review in book_reviews) / total_reviews
            else:
                average_rating = 0
            # Apply the minimum rating filter
            if average_rating >= min_rating:
                # Add the average rating and total reviews to the ebook object
                ebook.average_rating = average_rating
                ebook.total_reviews = total_reviews
                # Check if the user owns this ebook
                ebook.is_owned = ebook.get_ebook_id() in user_inventory
                ebooks_list.append(ebook)

    # Shuffle the ebooks_list to display books in random order
    random.shuffle(ebooks_list)

    # Get a list of unique genres for the filter dropdown
    genres = set(ebook.get_genre() for ebook in ebooks_dict.values())

    return render_template("Store.html", ebooks_list=ebooks_list, genres=genres,
                           selected_genre=selected_genre, min_price=min_price, max_price=max_price,
                           min_rating=min_rating, is_empty=is_empty)


@app.route('/book_details/<int:id>')
def display_book_details(id):
    if 'user_id' not in session:
        flash('You need to log in to view book details.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username', 'Unknown User')

    create_review_form = CreateReviewForm(request.form)

    # Open the inventory database to check if the user owns the ebook
    user_owns_ebook = False
    try:
        inventory_db = shelve.open('inventory.db', 'r')
        inventory_dict = inventory_db.get('Inventory', {})
        user_inventory = inventory_dict.get(user_id, [])
        user_owns_ebook = id in user_inventory
        inventory_db.close()
    except Exception as e:
        print(f"Error accessing inventory.db: {e}")

    # Open the ebooks database to get the ebook details
    db = shelve.open('ebooks.db', 'r')
    ebooks_dict = db['Ebooks']
    db.close()
    ebook = ebooks_dict.get(id)

    if not ebook:
        flash('Ebook not found.', 'error')
        return redirect(url_for('inventory'))

    # Open the reviews database (create if it doesn't exist)
    reviews_dict = {}
    try:
        db = shelve.open('reviews.db', 'c')
        try:
            reviews_dict = db.get('Reviews', {})
            if not reviews_dict:
                db['Reviews'] = {}
                reviews_dict = db['Reviews']
        except Exception as e:
            print(f"Error accessing reviews.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening reviews.db: {e}")

    # Filter reviews for the current ebook
    book_reviews = [review for review in reviews_dict.values() if review.get_ebook_id() == id]

    # Check if the user has already reviewed this ebook
    user_review = next((review for review in book_reviews if review.get_user_id() == user_id), None)

    # Calculate average rating and total reviews for the ebook
    total_reviews = len(book_reviews)
    if total_reviews > 0:
        average_rating = sum(review.get_stars() for review in book_reviews) / total_reviews
    else:
        average_rating = 0

    # Add the average rating and total reviews to the ebook object
    ebook.average_rating = average_rating
    ebook.total_reviews = total_reviews

    return render_template('book_details.html', ebook=ebook, reviews=book_reviews, form=create_review_form,
                           user_review=user_review, user_owns_ebook=user_owns_ebook)


@app.route('/create_review/<int:id>', methods=['POST'])
def create_review(id):
    if 'user_id' not in session:
        flash('You need to log in to leave a review.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username', 'Unknown User')
    create_review_form = CreateReviewForm(request.form)

    # Open the ebooks database to get the ebook details
    db = shelve.open('ebooks.db', 'r')
    ebooks_dict = db['Ebooks']
    db.close()
    ebook = ebooks_dict.get(id)
    if not ebook:
        flash('Ebook not found.', 'error')
        return redirect(url_for('inventory'))

    # Open the reviews database (create if it doesn't exist)
    reviews_dict = {}
    try:
        db = shelve.open('reviews.db', 'c')
        try:
            reviews_dict = db.get('Reviews', {})
            if not reviews_dict:
                db['Reviews'] = {}
                reviews_dict = db['Reviews']
        except Exception as e:
            print(f"Error accessing reviews.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening reviews.db: {e}")

    # Open the inventory database to check if the user owns the ebook
    user_owns_ebook = False
    try:
        inventory_db = shelve.open('inventory.db', 'r')
        inventory_dict = inventory_db.get('Inventory', {})
        user_inventory = inventory_dict.get(user_id, [])
        user_owns_ebook = id in user_inventory
        inventory_db.close()
    except Exception as e:
        print(f"Error accessing inventory.db: {e}")

    if not user_owns_ebook:
        flash('You must own the ebook to leave a review.', 'error')
        return redirect(url_for('display_book_details', id=id))

    if request.method == 'POST' and create_review_form.validate():
        stars = create_review_form.stars.data
        comment = create_review_form.comment.data
        anonymous = create_review_form.anonymous.data

        # Create a new review
        review = Review(user_id, username, id, stars, comment, anonymous)
        reviews_dict[review.get_review_id()] = review
        flash('Review submitted successfully!', 'success')

        # Save the reviews to the database
        db = shelve.open('reviews.db', 'c')
        try:
            db['Reviews'] = reviews_dict
        except Exception as e:
            print(f"Error saving review: {e}")
        finally:
            db.close()

        # Redirect back to the referring page (if available)
        referrer = request.referrer
        if referrer and ('reviews' in referrer or 'book_details' in referrer):
            return redirect(referrer)
        else:
            # Default fallback in case referrer is not available or invalid
            return redirect(url_for('display_book_details', id=id))

    # If the form validation fails, redirect back to the referring page
    referrer = request.referrer
    if referrer and ('reviews' in referrer or 'book_details' in referrer):
        return redirect(referrer)
    else:
        return redirect(url_for('display_book_details', id=id))


@app.route('/update_review/<int:id>', methods=['POST'])
def update_review(id):
    if 'user_id' not in session:
        flash('You need to log in to update a review.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username', 'Unknown User')
    create_review_form = CreateReviewForm(request.form)

    # Open the ebooks database to get the ebook details
    db = shelve.open('ebooks.db', 'r')
    ebooks_dict = db['Ebooks']
    db.close()

    ebook = ebooks_dict.get(id)
    if not ebook:
        flash('Ebook not found.', 'error')
        return redirect(url_for('inventory'))

    # Open the reviews database (create if it doesn't exist)
    reviews_dict = {}
    try:
        db = shelve.open('reviews.db', 'c')
        try:
            reviews_dict = db.get('Reviews', {})
            if not reviews_dict:
                db['Reviews'] = {}
                reviews_dict = db['Reviews']
        except Exception as e:
            print(f"Error accessing reviews.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening reviews.db: {e}")

    # Filter reviews for the current ebook
    book_reviews = [review for review in reviews_dict.values() if review.get_ebook_id() == id]

    # Check if the user has already reviewed this ebook
    user_review = next((review for review in book_reviews if review.get_user_id() == user_id), None)
    if not user_review:
        flash('You have not left a review for this ebook.', 'error')
        return redirect(url_for('display_book_details', id=id))

    if request.method == 'POST' and create_review_form.validate():
        stars = create_review_form.stars.data
        comment = create_review_form.comment.data
        anonymous = create_review_form.anonymous.data

        # Update the existing review
        user_review.set_stars(stars)
        user_review.set_comment(comment)
        user_review.set_anonymous(anonymous, username)

        flash('Review updated successfully!', 'success')

        # Save the reviews to the database
        db = shelve.open('reviews.db', 'c')
        try:
            db['Reviews'] = reviews_dict
        except Exception as e:
            print(f"Error saving review: {e}")
        finally:
            db.close()

        # Redirect back to the referring page (if available)
        referrer = request.referrer
        if referrer and ('reviews' in referrer or 'book_details' in referrer):
            return redirect(referrer)
        else:
            # Default fallback in case referrer is not available or invalid
            return redirect(url_for('display_book_details', id=id))

    # If the form validation fails, redirect back to the referring page
    referrer = request.referrer
    if referrer and ('reviews' in referrer or 'book_details' in referrer):
        return redirect(referrer)
    else:
        return redirect(url_for('display_book_details', id=id))


@app.route('/inventory')
def inventory():
    if 'user_id' not in session:
        flash('You need to log in to view your inventory.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    is_empty = True
    inventory_dict = {}

    # Open the inventory database with error handling
    try:
        inventory_db = shelve.open('inventory.db', 'r')
        try:
            inventory_dict = inventory_db.get('Inventory', {})
        except KeyError:
            print("No inventory found in the database.")
        finally:
            inventory_db.close()
    except Exception as e:
        print(f"An error occurred while opening inventory.db: {e}")

    # Get the user's inventory
    user_inventory = inventory_dict.get(user_id, [])
    is_empty = len(user_inventory) == 0

    # Get the ebooks in the user's inventory
    ebooks_list = []
    try:
        db = shelve.open('ebooks.db', 'r')
        try:
            ebooks_dict = db['Ebooks']
            for ebook_id in user_inventory:
                if ebook_id in ebooks_dict:
                    ebooks_list.append(ebooks_dict[ebook_id])
        except KeyError:
            print("No ebooks found in the database.")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening ebooks.db: {e}")

    return render_template('inventory.html', ebooks_list=ebooks_list, is_empty=is_empty)

    # Filter ebooks based on genre, price range, and minimum rating
    ebooks_list = []
    for ebook in ebooks_dict.values():
        if (not selected_genre or ebook.get_genre() == selected_genre) and \
           (min_price <= ebook.get_price() <= max_price):
            # Calculate average rating and total reviews for this book
            book_reviews = [review for review in reviews_dict.values() if review.get_ebook_id() == ebook.get_ebook_id()]
            total_reviews = len(book_reviews)
            if total_reviews > 0:
                average_rating = sum(review.get_stars() for review in book_reviews) / total_reviews
            else:
                average_rating = 0

            # Apply the minimum rating filter
            if average_rating >= min_rating:
                # Add the average rating and total reviews to the ebook object
                ebook.average_rating = average_rating
                ebook.total_reviews = total_reviews
                ebooks_list.append(ebook)

    # Shuffle the ebooks_list to display books in random order
    random.shuffle(ebooks_list)

    # Get a list of unique genres for the filter dropdown
    genres = set(ebook.get_genre() for ebook in ebooks_dict.values())

    return render_template("Store.html", ebooks_list=ebooks_list, genres=genres,
                           selected_genre=selected_genre, min_price=min_price, max_price=max_price,
                           min_rating=min_rating, is_empty=is_empty)

@app.route('/createCard', methods=['GET', 'POST'])
def create_card():
    create_card_form = CreateCardForm(request.form)
    if request.method == 'POST' and create_card_form.validate():
        # Extract form data
        first_name = create_card_form.first_name.data
        last_name = create_card_form.last_name.data
        card_number = create_card_form.card_number.data
        expiry_date = create_card_form.expiry_date.data  # Already a datetime.date object
        cvc_number = create_card_form.cvc_number.data

        # Validate card number
        if not re.match(r'^(4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|2[0-9]\d{14})$', card_number):
            flash('Invalid card number. It must be valid and follow standard card number formats.', 'error')
            return redirect(url_for('create_card'))

        # Validate expiry date
        from datetime import date
        if expiry_date < date.today():
            flash('Expiry date must be in the future.', 'error')
            return redirect(url_for('create_card'))

        # Validate CVC
        if not re.match(r'^\d{3}$', cvc_number):
            flash('Invalid CVC. It must be exactly 3 digits long.', 'error')
            return redirect(url_for('create_card'))

        # Open the database and check for duplicates
        cards_dict = {}
        db = shelve.open('card.db', 'c')
        try:
            cards_dict = db.get('Cards', {})
            for card in cards_dict.values():
                if card.get_card_number() == card_number:
                    flash('Duplicate card detected. This card already exists.', 'error')
                    return redirect(url_for('create_card'))
        finally:
            db.close()

        # If no duplicates, create the card
        card = Card(
            first_name,
            last_name,
            card_number,
            expiry_date,
            cvc_number
        )

        # Save the card to the database
        db = shelve.open('card.db', 'c')
        try:
            cards_dict[card.get_card_id()] = card
            db['Cards'] = cards_dict
        finally:
            db.close()

        # Redirect based on user role
        if 'role' in session and session['role'] in ['Owner', 'Co-owner']:
            flash('Card successfully added!', 'success')
            return redirect(url_for('retrieve_cards'))  # Owners and Co-owners go to retrieve_cards
        else:
            flash('Card successfully added!', 'success')
            return redirect(url_for('payment'))  # Non-owners and non-co-owners go to payment

    return render_template('createCard.html', form=create_card_form)


@app.route('/retrieveCard')
@staff_only
def retrieve_cards():
    if 'role' not in session or session['role'] not in ['Owner', 'Co-owner']:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))

    cards_dict = {}
    try:
        db = shelve.open('card.db', 'c')
        try:
            # Try to retrieve the 'Cards' dictionary
            cards_dict = db.get('Cards', {})  # Use .get() to avoid KeyError
            if not cards_dict:  # If 'Cards' key doesn't exist or is empty
                db['Cards'] = {}  # Initialize an empty dictionary
                cards_dict = db['Cards']
        except Exception as e:
            print(f"Error accessing card.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening card.db: {e}")

    cards_list = []
    for key in cards_dict:
        card = cards_dict.get(key)
        cards_list.append(card)

    return render_template('retrieveCard.html', count=len(cards_list), cards_list=cards_list)


@app.route('/update_user_card')
def update_user_card():
    if 'user_id' not in session:
        flash('You need to log in to update your card.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Open the card database to fetch the user's saved cards
    saved_cards = []
    try:
        db = shelve.open('card.db', 'r')
        cards_dict = db.get('Cards', {})
        saved_cards = [card for card in cards_dict.values() if card.get_user_id() == user_id]
        db.close()
    except Exception as e:
        print(f"Error accessing card.db: {e}")
        flash('An error occurred while fetching your saved cards.', 'error')
        return redirect(url_for('home'))

    return render_template('select_card_to_update.html', saved_cards=saved_cards)


@app.route('/delete_user_card/<int:id>', methods=['POST'])
def delete_user_card(id):
    if 'user_id' not in session:
        flash('You need to log in to delete a card.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Open the card database
    db = shelve.open('card.db', 'w')
    try:
        cards_dict = db.get('Cards', {})

        # Check if the card exists and belongs to the logged-in user
        card = cards_dict.get(id)
        if card and card.get_user_id() == user_id:
            del cards_dict[id]
            db['Cards'] = cards_dict
            flash('Card deleted successfully!', 'success')
        else:
            flash('Card not found or you do not have permission to delete it.', 'error')
    except Exception as e:
        print(f"Error deleting card: {e}")
        flash('An error occurred while deleting the card.', 'error')
    finally:
        db.close()

    return redirect(url_for('update_user_card'))

@app.route('/updateCard/<int:id>/', methods=['GET', 'POST'])
def update_card(id):
    update_card_form = CreateCardForm(request.form)
    if request.method == 'POST' and update_card_form.validate():
        cards_dict = {}
        db = shelve.open('card.db', 'w')
        cards_dict = db['Cards']

        card = cards_dict.get(id)
        card.set_first_name(update_card_form.first_name.data)
        card.set_last_name(update_card_form.last_name.data)
        card.set_card_number(update_card_form.card_number.data)
        card.set_expiry_date(update_card_form.expiry_date.data)
        card.set_cvc_number(update_card_form.cvc_number.data)

        db['Cards'] = cards_dict
        db.close()
        if 'role' not in session or session['role'] not in ['Staff', 'Owner', 'Co-owner']:
            return redirect(url_for('update_user_card'))
        else:
            return redirect(url_for('retrieve_cards'))

    else:
        cards_dict = {}
        db = shelve.open('card.db', 'r')
        cards_dict = db['Cards']
        db.close()

        card = cards_dict.get(id)
        update_card_form.first_name.data = card.get_first_name()
        update_card_form.last_name.data = card.get_last_name()
        update_card_form.card_number.data = card.get_card_number()
        update_card_form.expiry_date.data = card.get_expiry_date()
        update_card_form.cvc_number.data = card.get_cvc_number()

        return render_template('updateCard.html', form=update_card_form, card=card)

@app.route('/deleteCard/<int:id>', methods=['POST'])
@staff_only
def delete_card(id):
    if 'role' not in session or session['role'] not in ['Staff', 'Owner', 'Co-owner']:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))

    cards_dict = {}
    db = shelve.open('card.db', 'w')
    cards_dict = db['Cards']

    cards_dict.pop(id)

    db['Cards'] = cards_dict
    db.close()

    return redirect(url_for('retrieve_cards'))

@app.route('/createEbook', methods=['GET', 'POST'])
@staff_only
def create_ebook():
    if 'role' not in session or session['role'] not in ['Staff', 'Owner', 'Co-owner']:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))

    create_ebook_form = CreateEbookForm(request.form)
    if request.method == 'POST' and create_ebook_form.validate():
        # Handle cover image upload
        image_file = request.files.get('image')
        image_filename = None

        if image_file and allowed_file(image_file.filename):
            # Secure the filename and save it to the upload folder
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(image_path)
            image_filename = filename  # Store only the filename, not the full path

        # Handle book content upload
        content_file = request.files.get('content')
        content_filename = None

        if content_file and content_file.filename.endswith('.pdf'):
            # Secure the filename and save it to the upload folder
            filename = secure_filename(content_file.filename)
            content_path = os.path.join(UPLOAD_FOLDER, filename)
            content_file.save(content_path)
            content_filename = filename  # Store only the filename, not the full path

        # Create the ebook object
        ebook = Ebook(
            create_ebook_form.title.data,
            create_ebook_form.author.data,
            create_ebook_form.description.data,
            create_ebook_form.price.data,
            create_ebook_form.genre.data,
            image_filename,  # Save only the filename
            content_filename  # Save only the filename
        )

        # Save the ebook to the database
        ebooks_dict = {}
        db = shelve.open('ebooks.db', 'c')
        try:
            ebooks_dict = db['Ebooks']
        except KeyError:
            print("Error in retrieving Ebooks from ebooks.db.")
        ebooks_dict[ebook.get_ebook_id()] = ebook
        db['Ebooks'] = ebooks_dict
        db.close()

        return redirect(url_for('retrieve_ebooks'))
    return render_template('createEbook.html', form=create_ebook_form)

@app.route('/retrieveEbooks')
@staff_only
def retrieve_ebooks():
    if 'role' not in session or session['role'] not in ['Staff', 'Owner', 'Co-owner']:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))
    ebooks_dict = {}
    db = shelve.open('ebooks.db', 'r')
    try:
        ebooks_dict = db['Ebooks']
    except KeyError:
        print("No ebooks found in the database.")
    db.close()

    ebooks_list = list(ebooks_dict.values())
    return render_template('retrieveEbooks.html', count=len(ebooks_list), ebooks_list=ebooks_list)


@app.route('/updateEbook/<int:id>/', methods=['GET', 'POST'])
@staff_only
def update_ebook(id):
    update_ebook_form = CreateEbookForm(request.form)

    # Open the database in read mode to retrieve the ebook
    try:
        db = shelve.open('ebooks.db', 'r')
        ebooks_dict = db.get('Ebooks', {})
        db.close()
    except Exception as e:
        print(f"Error accessing ebooks.db: {e}")
        flash('An error occurred while accessing the ebook database.', 'error')
        return redirect(url_for('home'))

    # Check if the ebook exists
    ebook = ebooks_dict.get(id)
    if ebook is None:
        flash('Ebook not found.', 'error')
        return redirect(url_for('retrieve_ebooks'))

    if request.method == 'POST' and update_ebook_form.validate():
        # Open the database in write mode to update the ebook
        try:
            db = shelve.open('ebooks.db', 'w')
            ebooks_dict = db.get('Ebooks', {})

            # Update the ebook details
            ebook.set_title(update_ebook_form.title.data)
            ebook.set_author(update_ebook_form.author.data)
            ebook.set_description(update_ebook_form.description.data)
            ebook.set_price(update_ebook_form.price.data)
            ebook.set_genre(update_ebook_form.genre.data)

            # Handle image upload
            image_file = request.files.get('image')
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(image_path)
                ebook.set_image(filename)

            # Handle content upload
            content_file = request.files.get('content')
            if content_file and content_file.filename.endswith('.pdf'):
                filename = secure_filename(content_file.filename)
                content_path = os.path.join(UPLOAD_FOLDER, filename)
                content_file.save(content_path)
                ebook.set_content_path(filename)

            # Save the updated ebook back to the database
            ebooks_dict[id] = ebook
            db['Ebooks'] = ebooks_dict
            db.close()

            flash('Ebook updated successfully!', 'success')
            return redirect(url_for('retrieve_ebooks'))
        except Exception as e:
            print(f"Error updating ebook: {e}")
            flash('An error occurred while updating the ebook.', 'error')
            return redirect(url_for('retrieve_ebooks'))
    else:
        # Pre-fill the form with the existing ebook details
        update_ebook_form.title.data = ebook.get_title()
        update_ebook_form.author.data = ebook.get_author()
        update_ebook_form.description.data = ebook.get_description()
        update_ebook_form.price.data = ebook.get_price()
        update_ebook_form.genre.data = ebook.get_genre()

        return render_template('updateEbook.html', form=update_ebook_form, ebook=ebook)

@app.route('/deleteEbook/<int:id>', methods=['POST'])
@staff_only
def delete_ebook(id):
    if 'role' not in session or session['role'] not in ['Staff', 'Owner', 'Co-owner']:
        flash('Access denied!', 'error')
        return redirect(url_for('home'))

    ebooks_dict = {}
    db = shelve.open('ebooks.db', 'w')
    try:
        ebooks_dict = db['Ebooks']
        if id in ebooks_dict:
            # Remove the ebook from the database
            del ebooks_dict[id]
            db['Ebooks'] = ebooks_dict

        else:
            flash('Ebook not found.', 'error')
    except KeyError:
        flash('No ebooks found in the database.', 'error')
    db.close()

    return redirect(url_for('retrieve_ebooks'))

@app.route('/process_refund/<int:transaction_id>', methods=['POST'])
def process_refund(transaction_id):
    if 'user_id' not in session:
        flash('You need to log in to process a refund.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session.get('role', 'User')

    # Open the transactions database
    transaction_db = shelve.open('transactions.db', 'c')
    transactions_dict = transaction_db.get('Transactions', {})

    # Find the transaction
    transaction = transactions_dict.get(transaction_id)
    if not transaction:
        flash('Transaction not found.', 'error')
        return redirect(url_for('transaction_history'))

    # Check if the user is staff or the transaction belongs to the logged-in user
    if role not in ['Staff', 'Owner', 'Co-owner'] and transaction.get_user_id() != user_id:
        flash('You do not have permission to refund this transaction.', 'error')
        return redirect(url_for('transaction_history'))

    # Check if the transaction is already refunded
    if transaction.get_refund_status() == "Refunded":
        flash('This transaction has already been refunded.', 'error')
        return redirect(url_for('transaction_history'))

    # Open the inventory database
    inventory_db = shelve.open('inventory.db', 'c')
    inventory_dict = inventory_db.get('Inventory', {})

    # Remove the book from the user's inventory
    user_inventory = inventory_dict.get(transaction.get_user_id(), [])
    ebook_id_to_remove = None

    # Find the ebook ID associated with the transaction
    db = shelve.open('ebooks.db', 'r')
    ebooks_dict = db.get('Ebooks', {})
    for ebook_id, ebook in ebooks_dict.items():
        if ebook.get_title() == transaction.get_title():
            ebook_id_to_remove = ebook_id
            break
    db.close()

    if ebook_id_to_remove and ebook_id_to_remove in user_inventory:
        user_inventory.remove(ebook_id_to_remove)
        inventory_dict[transaction.get_user_id()] = user_inventory
        inventory_db['Inventory'] = inventory_dict

        # Update the transaction's refund status
        transaction.set_refund_status("Refunded")
        transactions_dict[transaction_id] = transaction
        transaction_db['Transactions'] = transactions_dict

        flash('Refund processed successfully. The book has been removed from the user\'s inventory.', 'success')
    else:
        flash('Failed to process refund. The book was not found in the user\'s inventory.', 'error')

    inventory_db.close()
    transaction_db.close()

    return redirect(url_for('transaction_history'))

@app.route('/transaction_history')
def transaction_history():
    if 'user_id' not in session:
        flash('You need to log in to view transaction history.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session.get('role', 'User')

    # Get filter parameters from the request
    filter_transaction_id = request.args.get('transaction_id', type=int)
    filter_user_id = request.args.get('user_id', type=int)  # New filter for user ID
    filter_username = request.args.get('username', '').strip()
    filter_book_title = request.args.get('book_title', '').strip()
    filter_refund_status = request.args.get('refund_status', '').strip()
    filter_amount_paid_min = request.args.get('amount_paid_min', type=float)
    filter_amount_paid_max = request.args.get('amount_paid_max', type=float)
    filter_transaction_date_start = request.args.get('transaction_date_start', '')
    filter_transaction_date_end = request.args.get('transaction_date_end', '')

    # Open the transactions database (create if it doesn't exist)
    transactions_dict = {}
    is_empty = True  # Assume there are no transactions by default
    try:
        db = shelve.open('transactions.db', 'c')
        try:
            transactions_dict = db.get('Transactions', {})  # Use .get() to avoid KeyError
            if not transactions_dict:  # If 'Transactions' key doesn't exist or is empty
                db['Transactions'] = {}  # Initialize an empty dictionary
                transactions_dict = db['Transactions']
            is_empty = len(transactions_dict) == 0  # Check if the transactions database is empty
        except Exception as e:
            print(f"Error accessing transactions.db: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"An error occurred while opening transactions.db: {e}")

    # Filter transactions based on user role
    if role in ['Staff', 'Owner', 'Co-owner']:
        # Owner sees only their transactions
        if role == 'Owner':
            transactions_list = [t for t in transactions_dict.values() if t.get_user_id() == user_id]
        else:
            transactions_list = list(transactions_dict.values())
    else:
        # Regular users can only view their own transactions
        transactions_list = [t for t in transactions_dict.values() if t.get_user_id() == user_id]

    # Helper function for partial matching
    def partial_match(text, filter_text):
        """
        Checks if filter_text matches any part of the text, considering spaces between words.
        """
        filter_words = filter_text.lower().split()
        text_words = text.lower().split()

        # Check if all filter words are found as prefixes of any word in the text
        return all(any(word.startswith(fw) for word in text_words) for fw in filter_words)

    # Apply additional filters if provided (inline logic for username and book title matching)
    if filter_transaction_id:
        transactions_list = [t for t in transactions_list if t.get_transaction_id() == filter_transaction_id]
    if filter_user_id:
        transactions_list = [t for t in transactions_list if t.get_user_id() == filter_user_id]  # Filter for user ID
    if filter_username:
        transactions_list = [t for t in transactions_list if partial_match(t.get_username(), filter_username)]
    if filter_book_title:
        transactions_list = [t for t in transactions_list if partial_match(t.get_title(), filter_book_title)]
    if filter_refund_status:  # Apply the refund status filter
        transactions_list = [t for t in transactions_list if t.get_refund_status().lower() == filter_refund_status.lower()]
    if filter_amount_paid_min is not None:
        transactions_list = [t for t in transactions_list if t.get_amount_paid() >= filter_amount_paid_min]
    if filter_amount_paid_max is not None:
        transactions_list = [t for t in transactions_list if t.get_amount_paid() <= filter_amount_paid_max]
    if filter_transaction_date_start:
        transactions_list = [t for t in transactions_list if t.get_timestamp().strftime('%Y-%m-%d') >= filter_transaction_date_start]
    if filter_transaction_date_end:
        transactions_list = [t for t in transactions_list if t.get_timestamp().strftime('%Y-%m-%d') <= filter_transaction_date_end]

    # Render the template with filtered transactions
    return render_template(
        'transaction_history.html',
        transactions=transactions_list,
        role=role,
        filter_transaction_id=filter_transaction_id,
        filter_user_id=filter_user_id,  # Pass the filter value for user_id
        filter_username=filter_username,
        filter_book_title=filter_book_title,
        filter_refund_status=filter_refund_status,
        filter_amount_paid_min=filter_amount_paid_min,
        filter_amount_paid_max=filter_amount_paid_max,
        filter_transaction_date_start=filter_transaction_date_start,
        filter_transaction_date_end=filter_transaction_date_end
    )


# Load the last used ebook_id from the database
def load_last_ebook_id():
    try:
        with shelve.open('ebooks.db', 'r') as db:
            ebooks_dict = db.get('Ebooks', {})
            if ebooks_dict:
                last_id = max(ebooks_dict.keys())
                Ebook.count_id = last_id
    except Exception as e:
        print(f"Error loading last ebook_id: {e}")

# Call this function when the application starts
load_last_ebook_id()

# Load the last used card_id from the database
def load_last_card_id():
    try:
        with shelve.open('card.db', 'r') as db:
            cards_dict = db.get('Cards', {})
            if cards_dict:
                last_id = max(cards_dict.keys())
                Card.count_id = last_id
    except Exception as e:
        print(f"Error loading last card_id: {e}")

# Call this function when the application starts
load_last_card_id()

def load_last_review_id():
    try:
        with shelve.open('reviews.db', 'r') as db:
            reviews_dict = db.get('Reviews', {})
            if reviews_dict:
                last_id = max(reviews_dict.keys())
                Review.count_id = last_id
    except Exception as e:
        print(f"Error loading last review_id: {e}")

# Call this function when the application starts
load_last_review_id()


if __name__ == "__main__":
    app.run()
