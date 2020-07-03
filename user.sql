CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR NOT NULL,
    pw VARCHAR NOT NULL
);

-- SELECT email, pw FROM users WHERE email = 'abc@abc.com' AND pw = 'abc'