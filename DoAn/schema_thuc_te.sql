-- Schema goi y neu nang cap do an thanh he thong thuc te.
-- File nay khong bat buoc chay cho demo hien tai, nhung dung de giai thich
-- huong mo rong: ca nhan hoa, ton kho, loi nhuan, khuyen mai, thoi gian mua.

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    segment TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    brand TEXT,
    price INTEGER NOT NULL,
    cost INTEGER,
    stock INTEGER DEFAULT 0,
    promotion_score REAL DEFAULT 0,
    icon TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    order_time TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS order_details (
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS category_compatibility (
    source_category TEXT NOT NULL,
    target_category TEXT NOT NULL,
    weight REAL DEFAULT 1,
    PRIMARY KEY (source_category, target_category)
);
