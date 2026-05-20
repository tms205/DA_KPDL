# ============================================================
# TRAIN MODEL GOI Y SAN PHAM BANG FP-GROWTH + LUAT KINH DOANH
# ============================================================
#
# NOTE DE HIEU BAI:
# File nay khong chi "chay FP-Growth roi in ra luat".
# Trong thuc te, he goi y nen co 2 tang:
#
#   Tang 1 - FP-Growth:
#       Hoc tu lich su hoa don de biet mon nao hay duoc mua chung.
#       Vi du: notebook + mouse -> keyboard.
#
#   Tang 2 - Business / Content-based Filtering:
#       Loc lai goi y theo danh muc hop ly, ton kho, khuyen mai, loi nhuan,
#       va khong goi y lai nhung mon khach da co trong gio hang.
#
# Du lieu demo hien tai chi co:
#   Ma_Hoa_Don, Ten_San_Pham
#
# Nen cac yeu to nhu so luong mua, thoi gian mua, loai khach hang, ton kho,
# khuyen mai se duoc thiet ke san trong backend de co the mo rong khi co
# du lieu that. Phan train van tao ra cac chi so FP-Growth cot loi:
# support, confidence, lift, leverage, conviction.
#
# Output:
#   - tap_luat_goi_y.csv : tap luat goi y da co score
#   - top_products.csv   : san pham pho bien de fallback khi cold-start
#   - model_report.txt   : bao cao danh gia model de dua vao do an

import math
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from fuzzywuzzy import process
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

DATA_FILE = Path("data_goc.csv")
DB_FILE = Path("database.db")
RULES_FILE = Path("tap_luat_goi_y.csv")
TOP_FILE = Path("top_products.csv")
REPORT_FILE = Path("model_report.txt")

# Nguong nay thap hon ban demo cu mot chut de khong bo sot luat tiem nang.
# Sau do ta se loc lai bang lift, leverage va support_count.
MIN_CONFIDENCE = 0.25
MIN_LIFT = 1.05

# Cho phep itemset dai toi da 3 de hoc duoc ngu canh:
#   laptop + mouse -> keyboard
# Neu max_len = 2 thi chi hoc duoc A -> B.
MAX_ITEMSET_LEN = 3
FUZZY_THRESHOLD = 80
TEST_RATIO = 0.2
RANDOM_STATE = 42
MAX_ONLINE_RETAIL_ITEMS = 300


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_master_categories():
    """Lay danh muc chuan tu SQLite de sua loi chinh ta va loc du lieu rac."""
    default_categories = [
        "smartphone",
        "notebook",
        "mouse",
        "keyboard",
        "monitor",
        "desktop",
        "headphone",
        "clocks",
        "printer",
        "tv",
    ]

    if not DB_FILE.exists():
        return default_categories

    try:
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute(
            "SELECT DISTINCT lower(trim(category)) FROM products"
        ).fetchall()
        conn.close()
        categories = sorted({row[0] for row in rows if row[0]})
        return categories or default_categories
    except sqlite3.Error:
        return default_categories


def normalize_item(raw_name, master_categories):
    """Sua loi chinh ta bang fuzzy matching.

    Vi du:
      smatphone -> smartphone
      mause     -> mouse

    Neu diem khop < 80 thi giu nguyen, sau do buoc clean se loai neu no
    khong nam trong danh muc chuan.
    """
    raw_name = str(raw_name).strip().lower()
    if not raw_name:
        return raw_name

    if not master_categories:
        return raw_name

    match = process.extractOne(raw_name, master_categories)
    if not match:
        return raw_name

    category, score = match
    return category if score >= FUZZY_THRESHOLD else raw_name


def standardize_transaction_columns(df):
    """Dua cac bo du lieu giao dich ve 2 cot chuan cua project.

    - Data cu: Ma_Hoa_Don, Ten_San_Pham.
    - Online Retail.xlsx: InvoiceNo, Description, Quantity.
    """
    columns = set(df.columns)
    if {"Ma_Hoa_Don", "Ten_San_Pham"}.issubset(columns):
        return df[["Ma_Hoa_Don", "Ten_San_Pham"]].copy(), True

    if {"InvoiceNo", "Description"}.issubset(columns):
        data = df.copy()
        if "Quantity" in data.columns:
            data = data[pd.to_numeric(data["Quantity"], errors="coerce") > 0]
        data = data[~data["InvoiceNo"].astype(str).str.startswith("C", na=False)]
        data = data.rename(
            columns={
                "InvoiceNo": "Ma_Hoa_Don",
                "Description": "Ten_San_Pham",
            }
        )
        return data[["Ma_Hoa_Don", "Ten_San_Pham"]].copy(), False

    raise ValueError(
        "File du lieu can co cot Ma_Hoa_Don/Ten_San_Pham "
        "hoac InvoiceNo/Description."
    )


def clean_transactions(df, master_categories, filter_to_master=True):
    """Lam sach du lieu giao dich truoc khi dua vao FP-Growth."""
    before = len(df)
    df = df.dropna(subset=["Ten_San_Pham", "Ma_Hoa_Don"]).copy()
    missing_rows = before - len(df)

    before = len(df)
    df = df.drop_duplicates().copy()
    duplicate_rows = before - len(df)

    before_values = df["Ten_San_Pham"].copy()
    if filter_to_master:
        df["Ten_San_Pham"] = df["Ten_San_Pham"].apply(
            lambda value: normalize_item(value, master_categories)
        )
        changed_rows = (before_values.astype(str).str.lower() != df["Ten_San_Pham"]).sum()
    else:
        df["Ten_San_Pham"] = (
            df["Ten_San_Pham"]
            .astype(str)
            .str.strip()
            .str.lower()
        )
        changed_rows = 0

    valid_categories = set(master_categories)
    before = len(df)
    if filter_to_master:
        df = df[df["Ten_San_Pham"].isin(valid_categories)].copy()
    unknown_rows = before - len(df)

    stats = {
        "missing_rows": missing_rows,
        "duplicate_rows": duplicate_rows,
        "changed_rows": int(changed_rows),
        "unknown_rows": unknown_rows,
        "clean_rows": len(df),
    }

    print(f"   - Removed missing rows: {missing_rows}")
    print(f"   - Removed duplicate rows: {duplicate_rows}")
    print(f"   - Normalized fuzzy names: {changed_rows}")
    print(f"   - Removed unknown categories: {unknown_rows}")
    print(f"   - Clean rows left: {len(df)}")
    return df, stats


def limit_high_cardinality_items(df, max_items=MAX_ONLINE_RETAIL_ITEMS):
    """Giam so luong mat hang cho bo Online Retail de FP-Growth chay on dinh."""
    counts = df["Ten_San_Pham"].value_counts()
    if len(counts) <= max_items:
        return df

    keep_items = set(counts.head(max_items).index)
    before = len(df)
    df = df[df["Ten_San_Pham"].isin(keep_items)].copy()
    print(f"   - Limited Online Retail items: {len(counts)} -> {max_items}")
    print(f"   - Rows removed by item limit: {before - len(df)}")
    return df


def build_baskets(df):
    """Gom cac dong cung Ma_Hoa_Don thanh 1 gio hang.

    FP-Growth can du lieu dang:
      [
        ["notebook", "mouse", "keyboard"],
        ["smartphone", "headphone"],
      ]

    Dung set de tranh 1 hoa don co lap lai cung 1 category lam sai y nghia
    "mua chung".
    """
    baskets = (
        df.groupby("Ma_Hoa_Don")["Ten_San_Pham"]
        .apply(lambda items: sorted(set(items)))
        .tolist()
    )
    return [basket for basket in baskets if len(basket) > 1]


def adaptive_support(total_baskets):
    """Chon min_support thich nghi theo kich thuoc data.

    Neu data nho ma support qua cao thi khong ra luat.
    Neu data lon ma support qua thap thi ra qua nhieu luat rac.

    Cong thuc:
      min_count = max(5, min(50, 0.2% so gio hang))
      min_support = min_count / tong so gio hang
    """
    min_count = max(5, min(50, math.ceil(total_baskets * 0.002)))
    min_support = min_count / total_baskets
    return min_count, min_support


def encode_baskets(baskets):
    """Bien gio hang thanh ma tran True/False cho FP-Growth."""
    encoder = TransactionEncoder()
    encoded = encoder.fit(baskets).transform(baskets)
    return pd.DataFrame(encoded, columns=encoder.columns_)


def add_rule_score(rules, total_baskets):
    """Them diem cho rule dua tren cac chi so cua association rules.

    Support:
      Mon A va B xuat hien chung nhieu hay it.

    Confidence:
      Trong nhung nguoi mua A, bao nhieu nguoi mua B.

    Lift:
      A va B co lien quan that su hay chi tinh co cung pho bien.

    Leverage / Conviction:
      Chi so bo sung giup loai bot rule yeu.

    Score o day la score cua rule, chua phai score san pham cuoi cung.
    Score san pham cuoi cung se duoc cong them Profit, Stock, Promotion
    trong main.py.
    """
    rules = rules.copy()
    rules["support_count"] = (rules["support"] * total_baskets).round().astype(int)
    rules["antecedent_len"] = rules["antecedents"].apply(len)
    rules["consequent_len"] = rules["consequents"].apply(len)

    max_lift = max(float(rules["lift"].max()), 1.0)
    max_support_count = max(int(rules["support_count"].max()), 1)
    conviction = rules["conviction"].replace([float("inf")], rules["conviction"].max())
    max_conviction = max(float(conviction.max()), 1.0)

    lift_norm = (rules["lift"] / max_lift).clip(upper=1)
    support_norm = (rules["support_count"] / max_support_count).clip(upper=1)
    conviction_norm = (conviction / max_conviction).clip(upper=1)

    # Cong thuc trong bai cua ban la:
    #   score = confidence * 0.4 + lift * 0.3 + profit * 0.2 + promotion * 0.1
    #
    # O file train chua co profit/promotion theo san pham cu the, nen ta tinh
    # rule_score truoc:
    #   rule_score = confidence * 0.4 + lift_norm * 0.3
    #              + support_norm * 0.2 + conviction_norm * 0.1
    #
    # Sang main.py, khi chon san pham that trong database, se cong them:
    #   profit_score, stock_score, promotion_score.
    rules["score"] = (
        rules["confidence"] * 0.40
        + lift_norm * 0.30
        + support_norm * 0.20
        + conviction_norm * 0.10
    )

    # Uu tien luat ngan gon de de giai thich khi bao ve.
    # Neu hai luat diem gan nhau, A -> B de hieu hon A + C -> B.
    rules["score"] = rules["score"] - ((rules["antecedent_len"] - 1) * 0.015)
    return rules


def mine_rules(baskets):
    """Chay FP-Growth va tra ve rules da loc."""
    total_baskets = len(baskets)
    min_count, min_support = adaptive_support(total_baskets)

    df_encoded = encode_baskets(baskets)
    frequent_itemsets = fpgrowth(
        df_encoded,
        min_support=min_support,
        use_colnames=True,
        max_len=MAX_ITEMSET_LEN,
    )

    if frequent_itemsets.empty:
        return pd.DataFrame(), min_count, min_support, 0

    rules = association_rules(
        frequent_itemsets,
        metric="confidence",
        min_threshold=MIN_CONFIDENCE,
    )

    if rules.empty:
        return pd.DataFrame(), min_count, min_support, len(frequent_itemsets)

    rules = add_rule_score(rules, total_baskets)

    # Loc rule yeu:
    # - confidence: xac suat mua kem phai du lon
    # - lift: lien quan that su, khong phai tinh co
    # - leverage > 0: mua chung cao hon ky vong ngau nhien
    # - consequent_len == 1: moi goi y tra ra 1 nhom san pham de UI de hien
    rules = rules[
        (rules["confidence"] >= MIN_CONFIDENCE)
        & (rules["lift"] >= MIN_LIFT)
        & (rules["leverage"] > 0)
        & (rules["support_count"] >= min_count)
        & (rules["consequent_len"] == 1)
    ].copy()

    return rules, min_count, min_support, len(frequent_itemsets)


def rank_categories_from_rules(rules, context_items, top_k=4):
    """Gom nhieu luat FP-Growth de goi y theo gio hang hien tai.

    Vi du gio hang co:
      [notebook, mouse]

    Ta khong chi tim notebook -> ...
    Ma gom tat ca rule khop:
      notebook -> mouse
      notebook -> keyboard
      notebook, mouse -> keyboard

    Neu san pham da nam trong context thi khong goi y lai.
    """
    context = set(context_items)
    scores = {}

    for _, rule in rules.iterrows():
        antecedents = set(rule["antecedents"])
        consequents = set(rule["consequents"])

        if not antecedents & context:
            continue

        # Khop day du antecedent thi diem cao hon khop mot phan.
        match_strength = 1.0 if antecedents.issubset(context) else 0.65

        for item in consequents:
            if item in context:
                continue
            scores[item] = scores.get(item, 0) + float(rule["score"]) * match_strength

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [item for item, _ in ranked[:top_k]]


def evaluate_hit_rate(rules, test_baskets, top_k=4):
    """Danh gia don gian: Hit@K tren tap test.

    Cach lam:
      1. Lay moi gio hang test co >= 2 mon.
      2. Giau di 1 mon cuoi cung lam "dap an".
      3. Dung cac mon con lai lam context de goi y top K.
      4. Neu dap an nam trong top K thi tinh la dung.

    Chi so nay khong hoan hao nhu he thong ecommerce lon, nhung rat tot cho
    do an vi chung minh model duoc danh gia tren du lieu test, khong chi in
    luat ra man hinh.
    """
    if rules.empty or not test_baskets:
        return 0, 0, 0.0

    hits = 0
    total = 0
    for basket in test_baskets:
        if len(basket) < 2:
            continue
        context = basket[:-1]
        answer = basket[-1]
        recommendations = rank_categories_from_rules(rules, context, top_k=top_k)
        hits += int(answer in recommendations)
        total += 1

    hit_rate = hits / total if total else 0.0
    return hits, total, hit_rate


def stringify_rules(rules):
    """Doi frozenset thanh chuoi de luu CSV cho backend doc."""
    if rules.empty:
        return rules

    result = rules.copy()
    result["antecedents"] = result["antecedents"].apply(
        lambda values: ", ".join(sorted(values))
    )
    result["consequents"] = result["consequents"].apply(
        lambda values: ", ".join(sorted(values))
    )
    return result


def write_report(report_lines):
    REPORT_FILE.write_text("\n".join(report_lines), encoding="utf-8")


def main():
    print("Step 1: Loading raw transaction data...")
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Cannot find {DATA_FILE}")

    df = pd.read_csv(DATA_FILE)
    df, filter_to_master = standardize_transaction_columns(df)
    raw_rows = len(df)
    print(f"   - Raw rows: {raw_rows}")

    print("Step 2: Cleaning and standardizing categories...")
    master_categories = load_master_categories()
    if filter_to_master:
        print(f"   - Master categories: {', '.join(master_categories)}")
    else:
        print("   - Detected Online Retail format; using product descriptions as items.")
    df, clean_stats = clean_transactions(df, master_categories, filter_to_master)
    if not filter_to_master:
        df = limit_high_cardinality_items(df)

    print("Step 3: Building popular fallback list...")
    top_products = df["Ten_San_Pham"].value_counts().head(20).reset_index()
    top_products.columns = ["item_name", "count"]
    top_products.to_csv(TOP_FILE, index=False)

    print("Step 4: Building baskets for FP-Growth...")
    baskets = build_baskets(df)
    total_baskets = len(baskets)
    print(f"   - Valid baskets: {total_baskets}")

    if total_baskets < 10:
        raise RuntimeError("Too few valid baskets to train association rules.")

    # Chia train/test de co danh gia hieu qua.
    baskets_series = pd.Series(baskets).sample(frac=1, random_state=RANDOM_STATE)
    split_index = int(len(baskets_series) * (1 - TEST_RATIO))
    train_baskets = baskets_series.iloc[:split_index].tolist()
    test_baskets = baskets_series.iloc[split_index:].tolist()

    print("Step 5: Mining rules on train set for evaluation...")
    eval_rules, eval_min_count, eval_min_support, eval_itemsets = mine_rules(train_baskets)
    hits, total_eval, hit_rate = evaluate_hit_rate(eval_rules, test_baskets, top_k=4)

    print("Step 6: Mining final rules on all data for production...")
    final_rules_raw, min_count, min_support, frequent_count = mine_rules(baskets)

    if final_rules_raw.empty:
        print("No strong rules after filtering. Fallback file was still created.")
        pd.DataFrame().to_csv(RULES_FILE, index=False)
        write_report(
            [
                "MODEL REPORT",
                f"Raw rows: {raw_rows}",
                f"Clean rows: {clean_stats['clean_rows']}",
                f"Valid baskets: {total_baskets}",
                "Strong rules: 0",
                "Recommendation will use popular fallback.",
            ]
        )
        return

    final_rules = stringify_rules(final_rules_raw)
    final_rules = final_rules[
        [
            "antecedents",
            "consequents",
            "support",
            "support_count",
            "confidence",
            "lift",
            "leverage",
            "conviction",
            "antecedent_len",
            "score",
        ]
    ].sort_values(
        by=["score", "confidence", "lift", "support_count"],
        ascending=False,
    )

    final_rules.to_csv(RULES_FILE, index=False)

    recommended_counts = final_rules["consequents"].value_counts().head(10)
    top_lift_rules = final_rules.sort_values(by="lift", ascending=False).head(10)

    report_lines = [
        "MODEL REPORT - FP-GROWTH RECOMMENDATION",
        "============================================================",
        f"Raw rows: {raw_rows}",
        f"Clean rows: {clean_stats['clean_rows']}",
        f"Missing rows removed: {clean_stats['missing_rows']}",
        f"Duplicate rows removed: {clean_stats['duplicate_rows']}",
        f"Fuzzy-normalized rows: {clean_stats['changed_rows']}",
        f"Unknown category rows removed: {clean_stats['unknown_rows']}",
        f"Valid baskets: {total_baskets}",
        f"Train baskets: {len(train_baskets)}",
        f"Test baskets: {len(test_baskets)}",
        f"Final min_support: {min_support:.5f}",
        f"Final min_count: {min_count}",
        f"Frequent itemsets: {frequent_count}",
        f"Strong rules exported: {len(final_rules)}",
        "",
        "Evaluation:",
        f"Hit@4: {hits}/{total_eval} = {hit_rate:.2%}",
        "",
        "Top 10 rules by lift:",
        top_lift_rules.to_string(index=False),
        "",
        "Most recommended categories:",
        recommended_counts.to_string(),
        "",
        "Huong cai tien thuc te:",
        "- Them cot user_id, order_time, quantity vao du lieu giao dich.",
        "- Them profit_margin, stock, promotion vao bang products.",
        "- Ket hop FP-Growth voi content-based filtering theo category/brand/price.",
        "- Khi user co lich su mua hang, cong them diem ca nhan hoa theo segment.",
    ]
    write_report(report_lines)

    print("\nTop recommendation rules:")
    print(final_rules.head(10).to_string(index=False))
    print("\nEvaluation:")
    print(f"   - Hit@4: {hits}/{total_eval} = {hit_rate:.2%}")
    print(f"   - Report: {REPORT_FILE}")
    print(f"\nDone. Exported {RULES_FILE}, {TOP_FILE}, and {REPORT_FILE}.")
    print("Restart backend with: uvicorn main:app --reload")


if __name__ == "__main__":
    main()

#uvicorn main:app --reload
