from pathlib import Path
from datetime import datetime
import hashlib
import secrets
import sqlite3
import sys
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
UI_DIR = ROOT_DIR / "UI"
DB_FILE = ROOT_DIR / "database.db"
RULES_FILE = ROOT_DIR / "tap_luat_goi_y.csv"
TOP_FILE = ROOT_DIR / "top_products.csv"

app = FastAPI(title="TechStore AI Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


@app.get("/")
def open_storefront():
    return RedirectResponse(url="/ui/index.html")


class CustomerInfo(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    phone: str = Field(..., min_length=9, max_length=15)
    email: str = Field("", max_length=120)
    address: str = Field(..., min_length=8, max_length=240)
    note: str = Field("", max_length=400)


class OrderItemInput(BaseModel):
    id: str
    quantity: int = Field(1, ge=1, le=20)


class OrderInput(BaseModel):
    customer: CustomerInfo
    items: list[OrderItemInput]
    payment_method: str = "COD"
    shipping_method: str = "standard"


class RegisterInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=5, max_length=120)
    phone: str = Field("", max_length=15)
    password: str = Field(..., min_length=6, max_length=80)


class LoginInput(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=80)


class ProductInput(BaseModel):
    id: str = Field("", max_length=40)
    category: str = Field(..., min_length=2, max_length=40)
    brand: str = Field(..., min_length=2, max_length=60)
    name: str = Field(..., min_length=2, max_length=160)
    price: int = Field(..., ge=0)
    icon: str = Field("fa-box", max_length=240)
    stock: int = Field(10, ge=0, le=10000)
    rating: float = Field(4.7, ge=0, le=5)


class OrderStatusInput(BaseModel):
    status: str = Field(..., min_length=2, max_length=40)


class AdminOrderInput(BaseModel):
    customer: CustomerInfo
    payment_method: str = Field("COD", max_length=40)
    shipping_method: str = Field("standard", max_length=40)
    status: str = Field(..., min_length=2, max_length=40)


class CustomerUpdateInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=5, max_length=120)
    phone: str = Field("", max_length=15)
    role: str = Field("customer", max_length=20)
    segment: str = Field("general", max_length=40)


class ContactInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=5, max_length=120)
    phone: str = Field("", max_length=15)
    message: str = Field(..., min_length=5, max_length=1000)


BRAND_ORIGINS = {
    "Apple": "Mỹ",
    "Samsung": "Hàn Quốc",
    "Xiaomi": "Trung Quốc",
    "Google": "Mỹ",
    "OPPO": "Trung Quốc",
    "Vivo": "Trung Quốc",
    "Asus": "Đài Loan",
    "Dell": "Mỹ",
    "HP": "Mỹ",
    "Lenovo": "Trung Quốc",
    "Acer": "Đài Loan",
    "MSI": "Đài Loan",
    "LG": "Hàn Quốc",
    "Logitech": "Thụy Sĩ",
    "Razer": "Mỹ",
    "Sony": "Nhật Bản",
    "Canon": "Nhật Bản",
    "Epson": "Nhật Bản",
}

CATEGORY_LABELS = {
    "smartphone": "Điện thoại",
    "notebook": "Laptop",
    "mouse": "Chuột",
    "keyboard": "Bàn phím",
    "monitor": "Màn hình",
    "desktop": "PC desktop",
    "headphone": "Tai nghe",
    "clocks": "Đồng hồ",
    "printer": "Máy in",
    "tv": "TV",
}

CATEGORY_FEATURES = {
    "smartphone": ["Màn hình sắc nét", "Camera AI", "Sạc nhanh", "Bảo hành 12 tháng"],
    "notebook": ["Hiệu năng cao", "SSD tốc độ nhanh", "Thiết kế di động", "Bảo hành 24 tháng"],
    "desktop": ["Hiệu năng ổn định", "Dễ nâng cấp", "Tản nhiệt tốt", "Bảo hành 24 tháng"],
    "monitor": ["Tấm nền chất lượng", "Tần số quét mượt", "Màu sắc chính xác", "Bảo hành 24 tháng"],
    "mouse": ["Cảm biến chính xác", "Thiết kế công thái học", "Độ trễ thấp", "Bảo hành 12 tháng"],
    "keyboard": ["Switch bền", "Gõ ổn định", "Kết nối linh hoạt", "Bảo hành 12 tháng"],
    "headphone": ["Âm thanh chi tiết", "Micro rõ", "Đeo thoải mái", "Bảo hành 12 tháng"],
    "clocks": ["Theo dõi sức khỏe", "Kết nối điện thoại", "Pin tối ưu", "Bảo hành 12 tháng"],
    "printer": ["In ổn định", "Chi phí vận hành tốt", "Dễ bảo trì", "Bảo hành 12 tháng"],
    "tv": ["Hình ảnh sắc nét", "Âm thanh sống động", "Smart TV", "Bảo hành 24 tháng"],
}

SHIPPING_OPTIONS = {
    "standard": {"label": "Giao tiêu chuẩn", "fee": 30000, "eta": "2-4 ngày"},
    "express": {"label": "Giao nhanh", "fee": 70000, "eta": "24-48 giờ"},
    "pickup": {"label": "Nhận tại cửa hàng", "fee": 0, "eta": "Trong ngày"},
}

# ============================================================
# NOTE DE HIEU BAI: CAC LUAT KINH DOANH THEM VAO FP-GROWTH
# ============================================================
#
# FP-Growth chi tra loi cau hoi:
#   "Khach mua A thi thuong mua B nao?"
#
# Nhung he thong thuc te con phai hoi tiep:
#   - B co hop ly voi A khong?
#   - B con hang khong?
#   - B co loi nhuan/khuyen mai tot khong?
#   - Khach da co B trong gio hang chua?
#   - Khach co gu gaming/van phong/Apple khong?
#
# Vi database demo chua co bang users, orders, order_details va cac cot
# profit_margin/stock/promotion, nen file nay mo phong cac yeu to do bang
# dictionary. Khi lam du lieu that, chi can chuyen cac dictionary nay thanh
# bang trong SQLite.

# Loc category hop ly de tranh goi y vo ly:
#   smartphone -> headphone, clocks
#   notebook   -> mouse, keyboard, monitor, headphone
#   desktop    -> monitor, mouse, keyboard, headphone
CATEGORY_COMPATIBILITY = {
    "smartphone": {"headphone", "clocks"},
    "notebook": {"mouse", "keyboard", "monitor", "headphone"},
    "desktop": {"monitor", "mouse", "keyboard", "headphone"},
    "monitor": {"desktop", "mouse", "keyboard"},
    "mouse": {"keyboard", "notebook", "desktop", "monitor"},
    "keyboard": {"mouse", "notebook", "desktop", "monitor"},
    "headphone": {"smartphone", "notebook", "desktop"},
    "clocks": {"smartphone", "headphone"},
    "printer": {"notebook", "desktop"},
    "tv": {"headphone", "smartphone"},
}

# Loi nhuan uoc luong theo nhom hang. Thuc te nen luu cot profit_margin
# trong bang products.
CATEGORY_PROFIT_MARGIN = {
    "smartphone": 0.10,
    "notebook": 0.09,
    "desktop": 0.11,
    "monitor": 0.13,
    "mouse": 0.24,
    "keyboard": 0.22,
    "headphone": 0.20,
    "clocks": 0.18,
    "printer": 0.14,
    "tv": 0.12,
}

# Nhom dang khuyen mai. Thuc te nen lay tu bang promotions.
PROMOTION_CATEGORIES = {"mouse", "keyboard", "headphone"}

# Ton kho demo. Thuc te nen lay tu cot stock trong products.
CATEGORY_STOCK = {
    "smartphone": 40,
    "notebook": 25,
    "desktop": 12,
    "monitor": 30,
    "mouse": 100,
    "keyboard": 85,
    "headphone": 75,
    "clocks": 45,
    "printer": 15,
    "tv": 18,
}

# Ca nhan hoa demo. Neu user_segment=gaming thi uu tien do gaming.
# Vi du API:
#   /api/recommend?item=notebook&context=notebook,mouse&user_segment=gaming
SEGMENT_KEYWORDS = {
    "gaming": ["gaming", "rog", "razer", "predator", "omen", "hyperx", "strix"],
    "office": ["dell", "thinkpad", "logitech", "ultrasharp", "laserjet"],
    "apple": ["iphone", "macbook", "apple", "airpods", "imac"],
}


def split_items(value):
    if pd.isna(value):
        return []
    return [item.strip().lower() for item in str(value).split(",") if item.strip()]


def load_rules():
    if not RULES_FILE.exists() or RULES_FILE.stat().st_size == 0:
        return pd.DataFrame()

    df = pd.read_csv(RULES_FILE)
    if df.empty:
        return df

    df["antecedent_items"] = df["antecedents"].apply(split_items)
    df["consequent_items"] = df["consequents"].apply(split_items)

    for column in ["score", "confidence", "lift", "support_count"]:
        if column not in df.columns:
            df[column] = 0

    return df


def load_top_products():
    if not TOP_FILE.exists() or TOP_FILE.stat().st_size == 0:
        return pd.DataFrame(columns=["item_name", "count"])
    return pd.read_csv(TOP_FILE)


print("Loading recommendation model...")
try:
    rules_df = load_rules()
    top_df = load_top_products()
    max_lift_value = max(float(rules_df["lift"].max()), 1.0) if not rules_df.empty else 1.0
    print(f"Loaded {len(rules_df)} rules and {len(top_df)} fallback categories.")
except Exception as exc:
    print(f"Cannot load recommendation files: {exc}")
    rules_df = pd.DataFrame()
    top_df = pd.DataFrame(columns=["item_name", "count"])
    max_lift_value = 1.0


def db_query(query, params=()):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def db_execute(query, params=()):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(password, stored_hash):
    try:
        salt, _ = stored_hash.split("$", 1)
    except ValueError:
        return False
    return hash_password(password, salt) == stored_hash


def public_user(row):
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "phone": row[3],
        "role": row[5],
        "segment": row[6],
        "created_at": row[7],
    }


def table_columns(cursor, table_name):
    return {column[1] for column in cursor.execute(f"PRAGMA table_info({table_name})")}


def ensure_default_accounts(cursor):
    now = datetime.now().isoformat(timespec="seconds")
    accounts = [
        ("admin", "Quản trị TechStore", "admin@techstore.vn", "0907123456", "admin123", "admin", "office"),
        ("demo", "Khách hàng demo", "khach@techstore.vn", "0907000000", "khach123", "customer", "gaming"),
    ]
    for user_id, name, email, phone, password, role, segment in accounts:
        exists = cursor.execute("SELECT id FROM users WHERE email = ?", (email.lower(),)).fetchone()
        if not exists:
            cursor.execute(
                """
                INSERT INTO users (id, name, email, phone, password_hash, role, segment, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, name, email.lower(), phone, hash_password(password), role, segment, now),
            )


def init_commerce_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer',
            segment TEXT DEFAULT 'general',
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS product_inventory (
            product_id TEXT PRIMARY KEY,
            stock INTEGER NOT NULL DEFAULT 0,
            sold INTEGER NOT NULL DEFAULT 0,
            rating REAL NOT NULL DEFAULT 4.7,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contact_messages (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Mới',
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT NOT NULL,
            note TEXT,
            subtotal INTEGER NOT NULL,
            shipping_fee INTEGER NOT NULL,
            discount INTEGER NOT NULL,
            total INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            shipping_method TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    if "user_id" not in table_columns(cursor, "orders"):
        cursor.execute("ALTER TABLE orders ADD COLUMN user_id TEXT")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            order_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            line_total INTEGER NOT NULL,
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
        """
    )
    now = datetime.now().isoformat(timespec="seconds")
    products = cursor.execute("SELECT id, category, brand, name FROM products").fetchall()
    for product_id, category, brand, name in products:
        exists = cursor.execute(
            "SELECT product_id FROM product_inventory WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if not exists:
            stock = CATEGORY_STOCK.get(category, 12) + stable_number(product_id, 0, 18)
            sold = stable_number(product_id + name, 18, 420)
            rating = round(4.2 + (stable_number(product_id + brand, 0, 8) / 10), 1)
            cursor.execute(
                """
                INSERT INTO product_inventory (product_id, stock, sold, rating, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (product_id, stock, sold, rating, now),
            )
    ensure_default_accounts(cursor)
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup_event():
    init_commerce_tables()


def stable_number(seed, minimum, maximum):
    value = sum(ord(char) for char in str(seed))
    return minimum + (value % (maximum - minimum + 1))


def get_product_inventory(product_id, category, brand, name):
    try:
        row = db_query(
            "SELECT stock, sold, rating FROM product_inventory WHERE product_id = ?",
            (product_id,),
        )
    except sqlite3.OperationalError:
        row = []
    if row:
        stock, sold, rating = row[0]
        return int(stock), int(sold), float(rating)
    return (
        CATEGORY_STOCK.get(category, 12) + stable_number(product_id, 0, 18),
        stable_number(product_id + name, 18, 420),
        round(4.2 + (stable_number(product_id + brand, 0, 8) / 10), 1),
    )


def product_from_row(row):
    product_id, category, brand, name, price, icon = row
    stock, sold, rating = get_product_inventory(product_id, category, brand, name)
    label = CATEGORY_LABELS.get(category, category)
    warranty_months = 24 if category in {"notebook", "desktop", "monitor", "tv"} else 12
    description = (
        f"{name} là sản phẩm {label.lower()} chính hãng từ {brand}, phù hợp cho "
        "nhu cầu học tập, làm việc, giải trí và nâng cấp hệ sinh thái công nghệ cá nhân."
    )

    return {
        "id": row[0],
        "category": category,
        "cat": category,
        "category_label": label,
        "brand": brand,
        "name": name,
        "price": price,
        "icon": icon,
        "stock": stock,
        "sold": sold,
        "rating": rating,
        "origin": BRAND_ORIGINS.get(brand, "Đang cập nhật"),
        "warranty_months": warranty_months,
        "features": CATEGORY_FEATURES.get(category, ["Hàng chính hãng", "Bảo hành tiêu chuẩn"]),
        "description": description,
        "is_promotion": category in PROMOTION_CATEGORIES,
    }


def is_category_compatible(candidate_category, context_items):
    """Loc goi y vo ly bang bang compatibility."""
    context = {item.strip().lower() for item in context_items if item.strip()}
    candidate = candidate_category.strip().lower()

    if candidate in context:
        return False

    primary_item = context_items[0].strip().lower() if context_items else ""
    allowed = set(CATEGORY_COMPATIBILITY.get(primary_item, set()))

    if not allowed:
        for item in context:
            allowed.update(CATEGORY_COMPATIBILITY.get(item, set()))

    return candidate in allowed if allowed else True


def normalize_profit_score(product):
    margin = CATEGORY_PROFIT_MARGIN.get(product["cat"], 0.10)
    estimated_profit = product["price"] * margin
    return min(estimated_profit / 5_000_000, 1.0)


def stock_score(category):
    stock = CATEGORY_STOCK.get(category, 10)
    if stock <= 0:
        return 0.0
    return min(stock / 50, 1.0)


def promotion_score(category):
    return 1.0 if category in PROMOTION_CATEGORIES else 0.0


def personalization_score(product, user_segment):
    if not user_segment:
        return 0.0

    keywords = SEGMENT_KEYWORDS.get(user_segment.strip().lower(), [])
    product_name = product["name"].lower()
    return 1.0 if any(keyword in product_name for keyword in keywords) else 0.0


def score_product(product, rule_score, user_segment=""):
    profit = normalize_profit_score(product)
    promo = promotion_score(product["cat"])
    stock = stock_score(product["cat"])
    personal = personalization_score(product, user_segment)

    return (
        rule_score
        + profit * 0.20
        + promo * 0.10
        + stock * 0.05
        + personal * 0.08
    )


def rule_business_score(rule, match_strength):
    confidence = float(rule.get("confidence", 0) or 0)
    lift_norm = min(float(rule.get("lift", 0) or 0) / max_lift_value, 1.0)
    support_count = float(rule.get("support_count", 0) or 0)
    support_bonus = min(support_count / 1000, 1.0) * 0.05

    return ((confidence * 0.40) + (lift_norm * 0.30) + support_bonus) * match_strength


def rank_recommendation_categories(context_items, limit):
    if rules_df.empty:
        return {}, "popular_fallback"

    context = {item.strip().lower() for item in context_items if item.strip()}
    best_by_category = {}

    for _, rule in rules_df.iterrows():
        antecedents = set(rule["antecedent_items"])
        consequents = [item for item in rule["consequent_items"] if item not in context]

        if not consequents:
            continue

        if antecedents.issubset(context):
            match_strength = 1.0
        elif len(context) == 1 and antecedents & context:
            match_strength = 0.55
        else:
            continue

        base_score = rule_business_score(rule, match_strength)
        for category in consequents:
            if not is_category_compatible(category, context_items):
                continue
            best_by_category[category] = max(
                best_by_category.get(category, 0),
                base_score,
            )

    ranked = dict(
        sorted(best_by_category.items(), key=lambda item: item[1], reverse=True)[
            :limit
        ]
    )
    return ranked, "association_rules" if ranked else "popular_fallback"


def fallback_categories(context_items, limit, already_selected=None):
    already_selected = set(already_selected or [])
    result = {}

    if not top_df.empty and "item_name" in top_df.columns:
        for index, item in enumerate(top_df["item_name"].dropna().astype(str)):
            category = item.strip().lower()
            if category in already_selected:
                continue
            if not is_category_compatible(category, context_items):
                continue

            result[category] = max(0.25 - index * 0.01, 0.05)
            if len(result) >= limit:
                break

    return result


def get_products_by_category(category_name):
    rows = db_query(
        """
        SELECT id, category, brand, name, price, icon
        FROM products
        WHERE lower(category) = lower(?)
        """,
        (category_name,),
    )
    return [product_from_row(row) for row in rows]


def pick_best_product(category_name, rule_score, excluded_ids=None, user_segment=""):
    excluded_ids = set(excluded_ids or [])
    products = [
        product
        for product in get_products_by_category(category_name)
        if product["id"] not in excluded_ids
    ]

    if not products:
        return {
            "id": "unknown",
            "cat": category_name,
            "category": category_name,
            "brand": "Hãng",
            "name": f"{category_name.capitalize()} Cao Cap",
            "price": 0,
            "icon": "fa-box",
            "score": rule_score,
        }

    best_product = max(
        products,
        key=lambda product: score_product(product, rule_score, user_segment),
    )
    best_product["score"] = round(
        score_product(best_product, rule_score, user_segment),
        4,
    )
    return best_product


def token_from_header(authorization):
    if not authorization:
        return ""
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


def get_user_by_token(authorization):
    token = token_from_header(authorization)
    if not token:
        return None
    rows = db_query(
        """
        SELECT u.id, u.name, u.email, u.phone, u.password_hash, u.role, u.segment, u.created_at
        FROM user_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
        """,
        (token,),
    )
    return public_user(rows[0]) if rows else None


def require_user(authorization):
    user = get_user_by_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập")
    return user


def require_admin(authorization):
    user = require_user(authorization)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền quản trị")
    return user


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "TechStore AI Commerce API",
        "rules": len(rules_df),
        "database": str(DB_FILE),
    }


@app.post("/api/auth/register")
def register_user(payload: RegisterInput):
    email = payload.email.strip().lower()
    exists = db_query("SELECT id FROM users WHERE email = ?", (email,))
    if exists:
        raise HTTPException(status_code=409, detail="Email đã được đăng ký")

    user_id = "U" + uuid4().hex[:10].upper()
    created_at = datetime.now().isoformat(timespec="seconds")
    db_execute(
        """
        INSERT INTO users (id, name, email, phone, password_hash, role, segment, created_at)
        VALUES (?, ?, ?, ?, ?, 'customer', 'general', ?)
        """,
        (
            user_id,
            payload.name.strip(),
            email,
            payload.phone.strip(),
            hash_password(payload.password),
            created_at,
        ),
    )
    return login_user(LoginInput(email=email, password=payload.password))


@app.post("/api/auth/login")
def login_user(payload: LoginInput):
    email = payload.email.strip().lower()
    rows = db_query(
        """
        SELECT id, name, email, phone, password_hash, role, segment, created_at
        FROM users
        WHERE email = ?
        """,
        (email,),
    )
    if not rows or not verify_password(payload.password, rows[0][4]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")

    token = secrets.token_urlsafe(32)
    created_at = datetime.now().isoformat(timespec="seconds")
    db_execute(
        "INSERT INTO user_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, rows[0][0], created_at),
    )
    return {"token": token, "user": public_user(rows[0])}


@app.get("/api/auth/me")
def get_current_user(authorization: str = Header("")):
    return require_user(authorization)


@app.post("/api/auth/logout")
def logout_user(authorization: str = Header("")):
    token = token_from_header(authorization)
    if token:
        db_execute("DELETE FROM user_sessions WHERE token = ?", (token,))
    return {"ok": True}


@app.get("/api/catalog/summary")
def get_catalog_summary():
    products = [
        product_from_row(row)
        for row in db_query("SELECT id, category, brand, name, price, icon FROM products")
    ]
    categories = {}
    brands = {}
    for product in products:
        categories.setdefault(
            product["category"],
            {
                "category": product["category"],
                "label": product["category_label"],
                "count": 0,
            },
        )
        categories[product["category"]]["count"] += 1
        brands[product["brand"]] = brands.get(product["brand"], 0) + 1

    return {
        "total_products": len(products),
        "categories": sorted(categories.values(), key=lambda item: item["label"]),
        "brands": [{"brand": brand, "count": count} for brand, count in sorted(brands.items())],
        "price": {
            "min": min([product["price"] for product in products], default=0),
            "max": max([product["price"] for product in products], default=0),
        },
        "shipping_options": SHIPPING_OPTIONS,
    }


@app.get("/api/products")
def get_all_products(
    search: str = "",
    category: str = "",
    brand: str = "",
    min_price: int | None = None,
    max_price: int | None = None,
    sort: str = "featured",
):
    products = [
        product_from_row(row)
        for row in db_query("SELECT id, category, brand, name, price, icon FROM products")
    ]

    keyword = search.strip().lower()
    if keyword:
        products = [
            product
            for product in products
            if keyword in product["name"].lower()
            or keyword in product["brand"].lower()
            or keyword in product["category_label"].lower()
            or keyword in product["category"].lower()
        ]

    if category:
        products = [
            product
            for product in products
            if product["category"].lower() == category.strip().lower()
        ]

    if brand:
        products = [
            product
            for product in products
            if product["brand"].lower() == brand.strip().lower()
        ]

    if min_price is not None:
        products = [product for product in products if product["price"] >= min_price]
    if max_price is not None:
        products = [product for product in products if product["price"] <= max_price]

    if sort == "price_asc":
        products.sort(key=lambda product: product["price"])
    elif sort == "price_desc":
        products.sort(key=lambda product: product["price"], reverse=True)
    elif sort == "name_asc":
        products.sort(key=lambda product: product["name"])
    elif sort == "sold_desc":
        products.sort(key=lambda product: product["sold"], reverse=True)
    else:
        products.sort(key=lambda product: (product["is_promotion"], product["rating"], product["sold"]), reverse=True)

    return products


@app.get("/api/products/{product_id}")
def get_product_detail(product_id: str):
    rows = db_query(
        """
        SELECT id, category, brand, name, price, icon
        FROM products
        WHERE id = ?
        """,
        (product_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_from_row(rows[0])


@app.post("/api/contact")
def create_contact_message(message: ContactInput):
    message_id = "MSG" + uuid4().hex[:8].upper()
    created_at = datetime.now().isoformat(timespec="seconds")
    db_execute(
        """
        INSERT INTO contact_messages (id, name, email, phone, message, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'Mới', ?)
        """,
        (
            message_id,
            message.name.strip(),
            message.email.strip().lower(),
            message.phone.strip(),
            message.message.strip(),
            created_at,
        ),
    )
    return {"id": message_id, "status": "Mới", "created_at": created_at}


@app.get("/api/recommend")
def get_recommendations(
    item: str,
    limit: int = 4,
    context: str = "",
    user_segment: str = "",
):
    limit = max(1, min(limit, 20))
    context_items = split_items(context) if context else []
    primary_item = item.strip().lower()

    if primary_item and primary_item not in context_items:
        context_items.insert(0, primary_item)

    category_scores, source = rank_recommendation_categories(context_items, limit)

    if len(category_scores) < limit:
        category_scores.update(
            fallback_categories(
                context_items,
                limit - len(category_scores),
                already_selected=category_scores.keys(),
            )
        )

    products = []
    used_product_ids = set()
    for category, rule_score in list(category_scores.items())[:limit]:
        product = pick_best_product(
            category,
            rule_score,
            excluded_ids=used_product_ids,
            user_segment=user_segment,
        )
        products.append(product)
        used_product_ids.add(product["id"])

    products = sorted(products, key=lambda product: product.get("score", 0), reverse=True)

    return {
        "item": primary_item,
        "context": context_items,
        "user_segment": user_segment,
        "source": source,
        "recommendations": products,
    }


def get_products_by_ids(product_ids):
    placeholders = ",".join("?" for _ in product_ids)
    rows = db_query(
        f"""
        SELECT id, category, brand, name, price, icon
        FROM products
        WHERE id IN ({placeholders})
        """,
        tuple(product_ids),
    )
    return {row[0]: product_from_row(row) for row in rows}


def calculate_order_totals(items):
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    discount = int(subtotal * 0.03) if subtotal >= 30_000_000 else 0
    return subtotal, discount


@app.post("/api/orders")
def create_order(order: OrderInput, authorization: str = Header("")):
    if not order.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    current_user = get_user_by_token(authorization)

    product_ids = [item.id for item in order.items]
    products_by_id = get_products_by_ids(product_ids)
    if len(products_by_id) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="Some products do not exist")

    normalized_items = []
    for item in order.items:
        product = products_by_id[item.id]
        stock = int(product.get("stock", 0))
        if item.quantity > stock:
            raise HTTPException(
                status_code=400,
                detail=f"{product['name']} chỉ còn {stock} sản phẩm",
            )
        normalized_items.append(
            {
                **product,
                "quantity": item.quantity,
                "line_total": product["price"] * item.quantity,
            }
        )

    subtotal, discount = calculate_order_totals(normalized_items)
    shipping = SHIPPING_OPTIONS.get(order.shipping_method, SHIPPING_OPTIONS["standard"])
    shipping_fee = shipping["fee"] if subtotal > 0 else 0
    if subtotal >= 50_000_000 and order.shipping_method != "express":
        shipping_fee = 0
    total = subtotal + shipping_fee - discount
    order_id = "TS" + datetime.now().strftime("%y%m%d") + uuid4().hex[:6].upper()
    created_at = datetime.now().isoformat(timespec="seconds")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO orders (
            id, user_id, customer_name, phone, email, address, note, subtotal,
            shipping_fee, discount, total, payment_method, shipping_method,
            status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            current_user["id"] if current_user else None,
            order.customer.name.strip(),
            order.customer.phone.strip(),
            order.customer.email.strip(),
            order.customer.address.strip(),
            order.customer.note.strip(),
            subtotal,
            shipping_fee,
            discount,
            total,
            order.payment_method,
            order.shipping_method,
            "Đã tiếp nhận",
            created_at,
        ),
    )
    cursor.executemany(
        """
        INSERT INTO order_items (
            order_id, product_id, product_name, price, quantity, line_total
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                order_id,
                item["id"],
                item["name"],
                item["price"],
                item["quantity"],
                item["line_total"],
            )
            for item in normalized_items
        ],
    )
    cursor.executemany(
        """
        UPDATE product_inventory
        SET stock = MAX(stock - ?, 0),
            sold = sold + ?,
            updated_at = ?
        WHERE product_id = ?
        """,
        [(item["quantity"], item["quantity"], created_at, item["id"]) for item in normalized_items],
    )
    conn.commit()
    conn.close()

    return {
        "id": order_id,
        "status": "Đã tiếp nhận",
        "created_at": created_at,
        "user_id": current_user["id"] if current_user else None,
        "customer": order.customer.dict(),
        "items": normalized_items,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee,
        "discount": discount,
        "total": total,
        "payment_method": order.payment_method,
        "shipping_method": order.shipping_method,
        "shipping_label": shipping["label"],
        "eta": shipping["eta"],
    }


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    rows = db_query(
        """
        SELECT id, user_id, customer_name, phone, email, address, note, subtotal,
               shipping_fee, discount, total, payment_method, shipping_method,
               status, created_at
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Order not found")

    row = rows[0]
    items = db_query(
        """
        SELECT product_id, product_name, price, quantity, line_total
        FROM order_items
        WHERE order_id = ?
        """,
        (order_id,),
    )
    return {
        "id": row[0],
        "user_id": row[1],
        "customer": {
            "name": row[2],
            "phone": row[3],
            "email": row[4],
            "address": row[5],
            "note": row[6],
        },
        "subtotal": row[7],
        "shipping_fee": row[8],
        "discount": row[9],
        "total": row[10],
        "payment_method": row[11],
        "shipping_method": row[12],
        "status": row[13],
        "created_at": row[14],
        "items": [
            {
                "id": item[0],
                "name": item[1],
                "price": item[2],
                "quantity": item[3],
                "line_total": item[4],
            }
            for item in items
        ],
    }


@app.get("/api/account/orders")
def get_my_orders(authorization: str = Header("")):
    user = require_user(authorization)
    rows = db_query(
        """
        SELECT id, subtotal, shipping_fee, discount, total, payment_method,
               shipping_method, status, created_at
        FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user["id"],),
    )
    return [
        {
            "id": row[0],
            "subtotal": row[1],
            "shipping_fee": row[2],
            "discount": row[3],
            "total": row[4],
            "payment_method": row[5],
            "shipping_method": row[6],
            "status": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]


@app.get("/api/admin/dashboard")
def admin_dashboard(authorization: str = Header("")):
    require_admin(authorization)
    product_count = db_query("SELECT COUNT(*) FROM products")[0][0]
    user_count = db_query("SELECT COUNT(*) FROM users WHERE role = 'customer'")[0][0]
    order_count = db_query("SELECT COUNT(*) FROM orders")[0][0]
    revenue = db_query("SELECT COALESCE(SUM(total), 0) FROM orders")[0][0]
    low_stock_rows = db_query(
        """
        SELECT p.id, p.category, p.brand, p.name, p.price, p.icon, i.stock
        FROM products p
        JOIN product_inventory i ON i.product_id = p.id
        WHERE i.stock <= 10
        ORDER BY i.stock ASC
        LIMIT 6
        """
    )
    recent_orders = db_query(
        """
        SELECT id, customer_name, phone, total, status, created_at
        FROM orders
        ORDER BY created_at DESC
        LIMIT 6
        """
    )
    return {
        "metrics": {
            "products": product_count,
            "customers": user_count,
            "orders": order_count,
            "revenue": revenue,
        },
        "low_stock": [
            {
                **product_from_row(row[:6]),
                "stock": row[6],
            }
            for row in low_stock_rows
        ],
        "recent_orders": [
            {
                "id": row[0],
                "customer_name": row[1],
                "phone": row[2],
                "total": row[3],
                "status": row[4],
                "created_at": row[5],
            }
            for row in recent_orders
        ],
    }


@app.get("/api/admin/orders")
def admin_orders(authorization: str = Header("")):
    require_admin(authorization)
    rows = db_query(
        """
        SELECT id, user_id, customer_name, phone, email, address, note, subtotal,
               shipping_fee, discount, total, payment_method, shipping_method,
               status, created_at
        FROM orders
        ORDER BY created_at DESC
        """
    )
    return [
        {
            "id": row[0],
            "user_id": row[1],
            "customer": {
                "name": row[2],
                "phone": row[3],
                "email": row[4],
                "address": row[5],
                "note": row[6],
            },
            "subtotal": row[7],
            "shipping_fee": row[8],
            "discount": row[9],
            "total": row[10],
            "payment_method": row[11],
            "shipping_method": row[12],
            "status": row[13],
            "created_at": row[14],
        }
        for row in rows
    ]


@app.patch("/api/admin/orders/{order_id}/status")
def admin_update_order_status(order_id: str, payload: OrderStatusInput, authorization: str = Header("")):
    require_admin(authorization)
    exists = db_query("SELECT id FROM orders WHERE id = ?", (order_id,))
    if not exists:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    db_execute("UPDATE orders SET status = ? WHERE id = ?", (payload.status.strip(), order_id))
    return get_order(order_id)


@app.put("/api/admin/orders/{order_id}")
def admin_update_order(order_id: str, payload: AdminOrderInput, authorization: str = Header("")):
    require_admin(authorization)
    exists = db_query("SELECT id FROM orders WHERE id = ?", (order_id,))
    if not exists:
        raise HTTPException(status_code=404, detail="Khong tim thay don hang")
    shipping = SHIPPING_OPTIONS.get(payload.shipping_method, SHIPPING_OPTIONS["standard"])
    subtotal = db_query("SELECT COALESCE(SUM(line_total), 0) FROM order_items WHERE order_id = ?", (order_id,))[0][0]
    discount = db_query("SELECT COALESCE(discount, 0) FROM orders WHERE id = ?", (order_id,))[0][0]
    shipping_fee = int(shipping["fee"])
    if subtotal >= 50_000_000 and payload.shipping_method != "express":
        shipping_fee = 0
    total = int(subtotal) + shipping_fee - int(discount)
    db_execute(
        """
        UPDATE orders
        SET customer_name = ?, phone = ?, email = ?, address = ?, note = ?,
            shipping_fee = ?, total = ?, payment_method = ?, shipping_method = ?, status = ?
        WHERE id = ?
        """,
        (
            payload.customer.name.strip(),
            payload.customer.phone.strip(),
            payload.customer.email.strip().lower(),
            payload.customer.address.strip(),
            payload.customer.note.strip(),
            shipping_fee,
            total,
            payload.payment_method.strip() or "COD",
            payload.shipping_method.strip() or "standard",
            payload.status.strip(),
            order_id,
        ),
    )
    return get_order(order_id)


@app.delete("/api/admin/orders/{order_id}")
def admin_delete_order(order_id: str, authorization: str = Header("")):
    require_admin(authorization)
    exists = db_query("SELECT id FROM orders WHERE id = ?", (order_id,))
    if not exists:
        raise HTTPException(status_code=404, detail="Khong tim thay don hang")
    db_execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
    db_execute("DELETE FROM orders WHERE id = ?", (order_id,))
    return {"ok": True}


@app.get("/api/admin/customers")
def admin_customers(authorization: str = Header("")):
    require_admin(authorization)
    rows = db_query(
        """
        SELECT u.id, u.name, u.email, u.phone, u.role, u.segment, u.created_at,
               COUNT(o.id) AS order_count,
               COALESCE(SUM(o.total), 0) AS total_spent
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "role": row[4],
            "segment": row[5],
            "created_at": row[6],
            "order_count": row[7],
            "total_spent": row[8],
        }
        for row in rows
    ]


@app.put("/api/admin/customers/{customer_id}")
def admin_update_customer(customer_id: str, payload: CustomerUpdateInput, authorization: str = Header("")):
    require_admin(authorization)
    current = db_query("SELECT id, role FROM users WHERE id = ?", (customer_id,))
    if not current:
        raise HTTPException(status_code=404, detail="Khong tim thay khach hang")
    email = payload.email.strip().lower()
    duplicated = db_query("SELECT id FROM users WHERE email = ? AND id <> ?", (email, customer_id))
    if duplicated:
        raise HTTPException(status_code=409, detail="Email da duoc su dung")
    role = payload.role.strip().lower() or "customer"
    if role not in {"customer", "admin"}:
        raise HTTPException(status_code=400, detail="Vai tro khong hop le")
    if current[0][1] == "admin" and role != "admin":
        admin_count = db_query("SELECT COUNT(*) FROM users WHERE role = 'admin'")[0][0]
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Khong the ha quyen admin cuoi cung")
    db_execute(
        """
        UPDATE users
        SET name = ?, email = ?, phone = ?, role = ?, segment = ?
        WHERE id = ?
        """,
        (
            payload.name.strip(),
            email,
            payload.phone.strip(),
            role,
            payload.segment.strip() or "general",
            customer_id,
        ),
    )
    return {"ok": True}


@app.delete("/api/admin/customers/{customer_id}")
def admin_delete_customer(customer_id: str, authorization: str = Header("")):
    require_admin(authorization)
    current = db_query("SELECT id, role FROM users WHERE id = ?", (customer_id,))
    if not current:
        raise HTTPException(status_code=404, detail="Khong tim thay khach hang")
    if current[0][1] == "admin":
        admin_count = db_query("SELECT COUNT(*) FROM users WHERE role = 'admin'")[0][0]
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Khong the xoa admin cuoi cung")
    db_execute("UPDATE orders SET user_id = NULL WHERE user_id = ?", (customer_id,))
    db_execute("DELETE FROM user_sessions WHERE user_id = ?", (customer_id,))
    db_execute("DELETE FROM users WHERE id = ?", (customer_id,))
    return {"ok": True}


@app.get("/api/admin/messages")
def admin_messages(authorization: str = Header("")):
    require_admin(authorization)
    rows = db_query(
        """
        SELECT id, name, email, phone, message, status, created_at
        FROM contact_messages
        ORDER BY created_at DESC
        """
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "message": row[4],
            "status": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


@app.delete("/api/admin/messages/{message_id}")
def admin_delete_message(message_id: str, authorization: str = Header("")):
    require_admin(authorization)
    exists = db_query("SELECT id FROM contact_messages WHERE id = ?", (message_id,))
    if not exists:
        raise HTTPException(status_code=404, detail="Khong tim thay lien he")
    db_execute("DELETE FROM contact_messages WHERE id = ?", (message_id,))
    return {"ok": True}


@app.post("/api/admin/products")
def admin_create_product(product: ProductInput, authorization: str = Header("")):
    require_admin(authorization)
    product_id = product.id.strip() or ("p" + uuid4().hex[:8])
    if db_query("SELECT id FROM products WHERE id = ?", (product_id,)):
        raise HTTPException(status_code=409, detail="Mã sản phẩm đã tồn tại")
    db_execute(
        """
        INSERT INTO products (id, category, brand, name, price, icon)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            product.category.strip(),
            product.brand.strip(),
            product.name.strip(),
            product.price,
            product.icon.strip() or "fa-box",
        ),
    )
    db_execute(
        """
        INSERT OR REPLACE INTO product_inventory (product_id, stock, sold, rating, updated_at)
        VALUES (?, ?, 0, ?, ?)
        """,
        (product_id, product.stock, product.rating, datetime.now().isoformat(timespec="seconds")),
    )
    return get_product_detail(product_id)


@app.put("/api/admin/products/{product_id}")
def admin_update_product(product_id: str, product: ProductInput, authorization: str = Header("")):
    require_admin(authorization)
    if not db_query("SELECT id FROM products WHERE id = ?", (product_id,)):
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    db_execute(
        """
        UPDATE products
        SET category = ?, brand = ?, name = ?, price = ?, icon = ?
        WHERE id = ?
        """,
        (
            product.category.strip(),
            product.brand.strip(),
            product.name.strip(),
            product.price,
            product.icon.strip() or "fa-box",
            product_id,
        ),
    )
    db_execute(
        """
        INSERT INTO product_inventory (product_id, stock, sold, rating, updated_at)
        VALUES (?, ?, COALESCE((SELECT sold FROM product_inventory WHERE product_id = ?), 0), ?, ?)
        ON CONFLICT(product_id) DO UPDATE SET
            stock = excluded.stock,
            rating = excluded.rating,
            updated_at = excluded.updated_at
        """,
        (
            product_id,
            product.stock,
            product_id,
            product.rating,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    return get_product_detail(product_id)


@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(product_id: str, authorization: str = Header("")):
    require_admin(authorization)
    used = db_query("SELECT order_id FROM order_items WHERE product_id = ? LIMIT 1", (product_id,))
    if used:
        raise HTTPException(status_code=409, detail="Sản phẩm đã có trong đơn hàng, không nên xóa")
    db_execute("DELETE FROM product_inventory WHERE product_id = ?", (product_id,))
    db_execute("DELETE FROM products WHERE id = ?", (product_id,))
    return {"ok": True}
