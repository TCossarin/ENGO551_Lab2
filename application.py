from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'secret_key'

# Database setup
engine = create_engine('postgresql://postgres:12345@localhost/postgres')
db = scoped_session(sessionmaker(bind=engine))


@app.route('/')
def home():                             # Home page route - redirects to login page if user is not logged in
    if 'username' in session:           # If user is logged in, show the home page
        return render_template('home.html', username=session['username'])
    
    return redirect(url_for('login'))   # Back to login page if no user is logged in


@app.route('/login', methods=['GET', 'POST'])
def login():                                # Login route to authenticate users
    if request.method == 'POST':
        # Get user from the database based on username and password
        user = db.execute("SELECT username FROM users WHERE username = :username AND password = :password",
                          {"username": request.form['username'], "password": request.form['password']}).fetchone()
        
        if user:                            # If user exists, start session, redirect to home
            session['username'] = user.username
            flash('Login successful.', 'success')
            return redirect(url_for('home'))
        
        else:                               # Login failed
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')    # Show login form


@app.route('/register', methods=['GET', 'POST'])
def register():                                 # Registration route for new users
    if request.method == 'POST':
        # Check if username already exists in the database
        if db.execute("SELECT username FROM users WHERE username = :username", {"username": request.form['username']}).fetchone():
            flash('Username already taken, please choose another', 'error')     # Username taken

        else:                                   # If username is available, add new user to database
            db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                       {"username": request.form['username'], "password": request.form['password']})
            db.commit()
            flash('Registration successful. You can now log in.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')     # Show registration form


@app.route('/logout')
def logout():                                   # Logout route to end session
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    
    return redirect(url_for('login'))           # Return to login


@app.route('/search')
def search():                                   # Search route for books in database
    query = request.args.get('query')
    results = db.execute("SELECT * FROM books WHERE isbn ILIKE :query OR title ILIKE :query OR author ILIKE :query",
                         {"query": f"%{query}%"}).fetchall() if query else []
    
    if results:
        return render_template('search_results.html', results=results)  # Show search results if query exists
    return redirect(url_for('home'))                                    # Redirect to home


@app.route('/book/<isbn>', methods=['GET', 'POST'])
def book(isbn):
    book_data = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn": isbn}).fetchall()

    if 'username' in session:
        review_exists = db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND username = :username",
                                   {"isbn": isbn, "username": session.get('username')}).fetchone()
    else:
        review_exists = False
    
    return render_template('book.html', book=book_data, reviews=reviews, review_exists=review_exists, isbn=isbn)


@app.route('/submit_review/<isbn>', methods=['POST'])
def submit_review(isbn):                                # Route for submitting a review
    if 'username' in session and request.method == 'POST':
        # Check if user already has a review
        if not db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND username = :username",
                          {"isbn": isbn, "username": session['username']}).fetchone():
            # Add new review to database
            db.execute("INSERT INTO reviews (isbn, username, comment, rating) VALUES (:isbn, :username, :comment, :rating)",
                       {"isbn": isbn, "username": session['username'], "comment": request.form['comment'], "rating": request.form['rating']})
            db.commit()
            flash('Review submitted successfully.', 'success')

        else:
            flash('You have already submitted a review for this book.', 'warning')
    return redirect(url_for('book', isbn=isbn))


@app.route('/delete_review/<isbn>', methods=['POST'])
def delete_review(isbn):                                # Route for deleting a user's review
    if 'username' in session:
        # Delete review from database
        db.execute("DELETE FROM reviews WHERE isbn = :isbn AND username = :username",
                   {"isbn": isbn, "username": session['username']})
        db.commit()
        flash("Your review has been successfully deleted.", 'success')
    else:
        flash('You must be logged in to delete a review.', 'error')
    return redirect(url_for('book', isbn=isbn))


@app.route('/query', methods=['GET'])
def query_books():
    isbn = request.args.get('isbn', '')
    
    if not isbn:
        return jsonify({'error': 'Missing ISBN'}), 400

    api_url = "https://www.googleapis.com/books/v1/volumes"
    try:
        response = requests.get(api_url, params={"q": f"isbn:{isbn}"})
        response.raise_for_status()
        session['api_response'] = response.json()
        return jsonify(response.json())
    
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
