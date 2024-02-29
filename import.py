import csv
import psycopg2


conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="12345",
    host="localhost",
)
cur = conn.cursor()

import os

# Get the current directory
current_directory = os.getcwd()
print(current_directory)


with open('books.csv', 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip header

    for row in reader:
        isbn, title, author, year = row
        cur.execute("INSERT INTO books (isbn, title, author, year) VALUES (%s, %s, %s, %s)", (isbn, title, author, year))

conn.commit()
cur.close()
conn.close()
