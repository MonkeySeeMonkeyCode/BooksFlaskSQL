import os
import requests

from flask import Flask, session, render_template, request, redirect, url_for, abort, jsonify, make_response
from flask_session import Session
from sqlalchemy import create_engine, cast, Numeric, String
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

notes = []

@app.route("/")
def index():
    if 'message' in session:
        message = session['message']
        session.pop('message')
        return render_template("index.html", welcome=message)
    elif 'user_id' not in session:
        session.clear()
        return render_template("index.html")
    else:
        return render_template("index.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/error")
def error():
    message_error = request.args['error']
    return render_template('error.html', message=message_error)

@app.route("/createUser", methods=["POST"])
def createUser():
    email = request.form.get("email")
    password = request.form.get("password")
    if password == None or email == None:
        return redirect(url_for('error',error="Invalid username/password."))
    elif db.execute("SELECT * FROM users WHERE email = :email", {"email": email}).rowcount > 0:
        return redirect(url_for('error',error="Username taken."))
    else:
        db.execute("INSERT INTO users (email,pw) VALUES (:email, :pw)",
                {"email": email, "pw": password})
        db.commit()
        row = db.execute("SELECT id FROM users WHERE email =:email", {"email": email}).fetchone()
        session["user_id"] = row["id"]
        session['message'] = "Successfully created!"
        return redirect(url_for('index'))

@app.route("/login", methods=["POST","GET"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    row = db.execute("SELECT id, email, pw FROM users WHERE email = :email AND pw = :password", {"email": email, "password": password}).fetchone()

    if password == None or email == None or row is None:
        return redirect(url_for('error',error="Invalid username/password. Gotta!"))
    elif row.id:
        notes = ["user and password found in database -  true"]
        session["user_id"] = row["id"]
        session["message"] = "Successfully logged in!"
        return redirect(url_for('search'))
    else:
        return redirect(url_for('error',error="Invalid username/password. Catch them all!"))

@app.route("/logout")
def logout():
    if session.get('user_id'):
        session.pop('user_id')
        session['message'] = "logged out"
    
    return redirect(url_for('index'))

@app.route("/search", methods=["GET","POST"])
def search():
    if request.method == "GET":
        return render_template("search.html")
    
    if request.method == "POST":
        isbn = request.form.get("isbn")
        title = request.form.get("title")
        author = request.form.get("author")

        # sql='SELECT * FROM books WHERE isbn ILIKE :isbn OR title ILIKE :title OR author ILIKE :author'
        # args={"isbn": isbn+'%', "title": title+'%', "author": author+'%'}
        # results = db.execute(sql,args)

        if isbn:
            sql='SELECT * FROM books WHERE isbn ILIKE :isbn'
            args={"isbn": isbn+'%'}
            results = db.execute(sql,args).fetchall()
        elif title:
            sql='SELECT * FROM books WHERE title ILIKE :title'
            args={"title": title+'%'}
            results = db.execute(sql,args).fetchall()
        elif author:
            sql='SELECT * FROM books WHERE author ILIKE :author'
            args={"author": author+'%'}
            results = db.execute(sql,args).fetchall()

        # results = db.execute("SELECT * FROM books WHERE isbn = :isbn OR title = :title OR author = :author",
        #             {"isbn": isbn, "title": title, "author": author}).fetchall()

        # sql='SELECT * FROM books WHERE title ILIKE :title'
        # args={"title": title+'%'}
        # results = db.execute(sql,args)

        # if isbn:
        #     results = db.execute("SELECT * FROM books WHERE isbn= :isbn", {"isbn": isbn}).fetchall()
        # elif title:
        #     results = db.execute("SELECT * FROM books WHERE title= :title", {"title": title}).fetchall()
        # elif author:
        #     results = db.execute("SELECT * FROM books WHERE author= :author", {"author": author}).fetchall()
        
        if not results:
            return render_template("search.html", no_results="No results found")
        else:
            return render_template("search.html", results=results)

@app.route("/book", methods=["GET","POST"])
def book():
    if request.method == "GET":
        book_id = request.args['id']
        book = db.execute("SELECT * FROM books WHERE id = :book_id", {"book_id": book_id}).fetchone()
        # sql='SELECT * FROM books WHERE isbn ILIKE :isbn'
        #     args={"isbn": isbn+'%'}
        #     results = db.execute(sql,args).fetchall()
        sql = "SELECT user_id, review, rating, users.email FROM reviews INNER JOIN users on reviews.user_id=users.id WHERE reviews.book_id = :book_id"
        args = {"book_id": book_id}
        reviews = db.execute(sql,args).fetchall()
        # reviews = db.execute("SELECT user_id, review, rating, email FROM reviews WHERE book_id = :book_id LEFT OUTER JOIN users ON reviews.users_id = :user_id",
        #         {"user_id": user_id,"book_id": book_id})
        req_string = "https://www.goodreads.com/book/review_counts.json?isbns="+ str(book['isbn']).zfill(10) +"&key=lBoIRE6NaFIC5gCsdWjouQ"
        res = requests.get(req_string).json()
        # goodreads = [res['average_rating'],res['reviews_count']]
        # return render_template("book.html",book=book,reviews=reviews,goodreads=goodreads)
        return render_template("book.html",book=book,reviews=reviews,goodreads=res)
    if request.method == "POST":
        if not session.get('user_id'):
            return redirect(url_for('error',error="Please log in to leave a review."))
        book_id = request.form.get("book_id")
        user_id = session.get('user_id')
        if db.execute("SELECT book_id, user_id FROM reviews WHERE book_id = :book_id AND user_id = :user_id",
                {"book_id": book_id, "user_id": user_id}).fetchone():
            return redirect(url_for('error',error="One review per account."))
        book = db.execute("SELECT * FROM books WHERE id = :book_id", {"book_id": book_id}).fetchone()
        review = request.form.get("review_text")
        rating = request.form.get("rating_radio")
        user = db.execute("SELECT email FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()
        db.execute("INSERT INTO reviews (book_id,user_id,review,rating) VALUES (:book_id, :user_id, :review, :rating)",
                {"book_id": book_id, "user_id": user_id, "review": review, "rating": rating})
        db.commit()
        # reviews = db.execute("SELECT user_id, review, rating, email FROM reviews LEFT OUTER JOIN users ON users.id = user_id")
        # reviews = db.execute("SELECT user_id, review, rating, email FROM reviews WHERE book_id = :book_id LEFT OUTER JOIN users ON reviews.users_id = :user_id",
        #         {"user_id": user_id,"book_id": book_id})
        sql = "SELECT user_id, review, rating, users.email FROM reviews INNER JOIN users on reviews.user_id=users.id WHERE reviews.book_id = :book_id"
        args = {"book_id": book_id}
        reviews = db.execute(sql,args).fetchall()
        return render_template("book.html",book=book,reviews=reviews)
        # return render_template("book.html",book=book,reviews=[[review,rating,type(user_id),user,book_id],[review,rating,user_id,user,book_id]])

@app.route("/api/<int:isbn>", methods=["GET"])
def api_isbn(isbn):
    book = db.execute("SELECT id, title, author, year, isbn FROM books WHERE isbn = :isbn", {"isbn": str(isbn).zfill(10)}).fetchone()
    reviewproxy = db.execute("SELECT AVG(rating), COUNT(id) FROM reviews WHERE book_id = :book_id", {"book_id": book['id']})
    book_obj = {}
    book_obj['title'] = book['title']
    book_obj['author'] = book['author']
    book_obj['year'] = int(book['year'])
    book_obj['isbn'] = book['isbn']

    for review in reviewproxy:
        for avg, count in review.items():
            if review[0]:
                book_obj['average_score'] = float((review[0]))
            else: 
                book_obj['average_score'] = 0
            book_obj['review_count'] = review[1]

    if not book:
        abort(404) 
    return jsonify({'book': book_obj})

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)