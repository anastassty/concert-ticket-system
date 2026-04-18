import os
from flask import Flask, render_template, request
import psycopg2

# Connect to PostgreSQL database on Render
DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
cursor = conn.cursor()

app = Flask(__name__)

# Home page
@app.route("/")
def home():
    return render_template("home.html")

# Create all tables if they don't exist
@app.route("/create_tables")
def create_tables():
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS artist(
                        artist_id SERIAL PRIMARY KEY,
                        artist_name VARCHAR(100) NOT NULL,
                        genre VARCHAR(50) NOT NULL    
                    );
                    ''')
    
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS concert(
                        concert_id SERIAL PRIMARY KEY,
                        venue_name VARCHAR(100) NOT NULL,
                        city VARCHAR(50) NOT NULL,
                        concert_date DATE NOT NULL,
                        artist_id INT REFERENCES artist (artist_id)
                    );
                    ''')
    
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS customer(
                        customer_id SERIAL PRIMARY KEY,
                            customer_name VARCHAR(100) NOT NULL
                    );
                    ''')
    
    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ticket(
                        ticket_id SERIAL PRIMARY KEY,
                        concert_id INT REFERENCES concert (concert_id),
                        customer_id INT REFERENCES customer (customer_id),
                        seat_number VARCHAR(20),
                        price NUMERIC(10, 2)
                    );
                    ''')
    
    conn.commit()
    return "Tables created!"

# Add a new artist to the database
@app.route("/add_artist", methods=["GET", "POST"])
def add_artist():
    message = None
    if request.method == "POST":
        artist_name = request.form["artist_name"]
        genre = request.form["genre"]

        cursor.execute("INSERT INTO artist (artist_name, genre) VALUES (%s, %s);", (artist_name, genre))
        conn.commit()
        message = "Artist added successfully!"
    return render_template("add_artist.html", message=message)

# Add a new concert to the database
@app.route("/add_concert", methods=["GET", "POST"])
def add_concert():
    message = None
    cursor.execute("SELECT artist_id, artist_name FROM artist ORDER BY artist_name;")
    artists = cursor.fetchall()

    if request.method == "POST":
        venue_name = request.form["venue_name"]
        city = request.form["city"]
        concert_date = request.form["concert_date"]
        artist_id = request.form["artist_id"]

        cursor.execute('''
                       INSERT INTO concert (venue_name, city, concert_date, artist_id)
                       VALUES (%s, %s, %s, %s);
                       ''',
                        (venue_name, city, concert_date, artist_id))
        conn.commit()
        message = "Concert added successfully!"
    return render_template("add_concert.html", artists=artists, message=message)

# Add a new customer to the database
@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    message = None
    if request.method == "POST":
        customer_name = request.form["customer_name"]

        cursor.execute("INSERT INTO customer (customer_name) VALUES (%s);", (customer_name,))
        conn.commit()
        message = "Customer added successfully!"
    return render_template("add_customer.html", message=message)

# Add a new ticket purchase to the database
@app.route("/add_ticket", methods=["GET", "POST"])
def add_ticket():
    message = None
    cursor.execute('''
                   SELECT concert.concert_id, concert.venue_name, concert.city, concert.concert_date, artist.artist_name 
                   FROM concert 
                   JOIN artist ON concert.artist_id = artist.artist_id
                   ORDER BY concert.concert_date;
                   ''')
    concerts = cursor.fetchall()
    cursor.execute("SELECT customer_id, customer_name FROM customer ORDER BY customer_name;")
    customers = cursor.fetchall()

    if request.method == "POST":
        concert_id = request.form["concert_id"]
        customer_id = request.form["customer_id"]
        seat_number = request.form["seat_number"]
        price = request.form["price"]

        cursor.execute('''
                       INSERT INTO ticket (concert_id, customer_id, seat_number, price) 
                       VALUES (%s, %s, %s, %s);
                       ''',
                       (concert_id, customer_id, seat_number, price))
        conn.commit()
        message = "Ticket added successfully!"
    return render_template("add_ticket.html", concerts=concerts, customers=customers, message=message)

# View all concerts or filter by city
@app.route("/view_concerts", methods=["GET", "POST"])
def view_concerts():
    rows = []

    cursor.execute("SELECT DISTINCT city FROM concert ORDER BY city;")
    cities = [row[0] for row in cursor.fetchall()]

    if request.method == "POST":
        city = request.form["city"]

        if city == "all":
            cursor.execute('''
                           SELECT concert.concert_id, concert.venue_name, concert.city, concert.concert_date, artist.artist_name
                           FROM concert
                           JOIN artist ON concert.artist_id = artist.artist_id
                           ORDER BY concert.concert_date;
                           ''')
        else:
            cursor.execute('''
                           SELECT concert.concert_id, concert.venue_name, concert.city, concert.concert_date, artist.artist_name
                           FROM concert
                           JOIN artist ON concert.artist_id = artist.artist_id
                           WHERE concert.city = %s;
                           ''',
                           (city,))
            
        rows = cursor.fetchall()
    return render_template("view_concerts.html", rows=rows, cities = cities)

# View all concerts for a given artist
@app.route("/artist_concerts", methods=["GET", "POST"])
def artist_concerts():
    rows = []
    cursor.execute("SELECT artist_id, artist_name FROM artist ORDER BY artist_name;")
    artists = cursor.fetchall()

    if request.method == "POST":
        artist_id = request.form["artist_id"]

        cursor.execute('''
            SELECT artist.artist_name, concert.venue_name, concert.city, concert.concert_date
            FROM artist
            JOIN concert on artist.artist_id = concert.artist_id
            WHERE artist.artist_id = %s;
        ''',
        (artist_id,))
        rows = cursor.fetchall()
    return render_template("artist_concerts.html", rows=rows, artists=artists)

# View total spending per customer
@app.route("/customer_spending", methods=["GET", "POST"])
def customer_spending():
    rows = []
    cursor.execute("SELECT customer_id, customer_name FROM customer ORDER BY customer_name;")
    customers = cursor.fetchall()

    if request.method == "POST":
        customer_id = request.form["customer_id"]

        if customer_id == "all":
            cursor.execute('''
                SELECT customer.customer_id, customer.customer_name, COALESCE(SUM(ticket.price), 0) AS total_spent
                FROM customer
                LEFT JOIN ticket ON customer.customer_id = ticket.customer_id
                GROUP BY customer.customer_id, customer.customer_name
                ORDER BY customer.customer_id;                     
        ''')
        else:
            cursor.execute('''
                SELECT customer.customer_id, customer.customer_name, COALESCE(SUM(ticket.price), 0) AS total_spending
                FROM customer
                LEFT JOIN ticket ON customer.customer_id = ticket.customer_id
                WHERE customer.customer_id = %s
                GROUP BY customer.customer_id, customer.customer_name
                ORDER BY customer.customer_id;                     
        ''',
        (customer_id,))
        rows = cursor.fetchall()
    return render_template("customer_spending.html", rows=rows, customers=customers)

# Find top 3 artists by total ticket revenue
@app.route("/top_artists")
def top_artists():
    cursor.execute('''
        SELECT artist.artist_name, COALESCE(SUM(ticket.price), 0) AS total_revenue
        FROM artist
        JOIN concert ON artist.artist_id = concert.artist_id
        JOIN ticket ON concert.concert_id = ticket.concert_id
        GROUP BY artist.artist_id, artist.artist_name
        ORDER BY total_revenue DESC
        LIMIT 3;
    ''')
    rows = cursor.fetchall()

    return render_template("top_artists.html", rows=rows)

if __name__ == "__main__":
    app.run(debug=True)