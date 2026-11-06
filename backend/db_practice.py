import sqlite3

conn = sqlite3.connect("practice.db")
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

# ----- ساخت جدول‌ها -----
cur.executescript("""
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    price       INTEGER NOT NULL CHECK (price >= 0),
    category_id INTEGER NOT NULL,
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
""")

# ----- درج داده -----
cur.executemany(
    "INSERT INTO categories (name) VALUES (?)",
    [("قالب",), ("افزونه",)],
)

cur.executemany(
    "INSERT INTO products (name, price, category_id) VALUES (?, ?, ?)",
    [
        ("قالب فروشگاهی نمونه", 490000, 1),
        ("قالب شرکتی مینیمال", 390000, 1),
        ("افزونه فرم‌ساز", 290000, 2),
        ("افزونه سئو", 350000, 2),
    ],
)
conn.commit()

# افزونه‌های ارزان‌تر از ۳۰۰ هزار تومان
cur.execute("""
    SELECT name, price FROM products
    WHERE category_id = 2 AND price < 300000
""")
print(cur.fetchall())

# جستجو در نام (LIKE)
cur.execute("SELECT name FROM products WHERE name LIKE ?", ("%قالب%",))
print(cur.fetchall())

# تعداد و میانگین قیمت هر دسته (GROUP BY)
cur.execute("""
    SELECT categories.name, COUNT(*), AVG(products.price)
    FROM products
    JOIN categories ON products.category_id = categories.id
    GROUP BY categories.id
""")
print(cur.fetchall())

# تغییر قیمت (UPDATE) و حذف (DELETE)
cur.execute("UPDATE products SET price = ? WHERE id = ?", (450000, 1))
cur.execute("DELETE FROM products WHERE id = ?", (4,))
conn.commit()

# ----- خواندن با JOIN -----
rows = cur.execute("""
    SELECT products.name, products.price, categories.name
    FROM products
    JOIN categories ON products.category_id = categories.id
    ORDER BY products.price DESC
""").fetchall()

for name, price, category in rows:
    print(f"{name} | {price:,} تومان | {category}")

conn.close()

