CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books,
    user_id INTEGER REFERENCES users,
    review VARCHAR NOT NULL,
    review_date TIMESTAMP ,
    rating INTEGER NOT NULL
);