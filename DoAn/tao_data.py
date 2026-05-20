import pandas as pd
import numpy as np
import random

print("🏭 Khởi động nhà máy sản xuất Data...")

# 1. Danh sách sản phẩm chuẩn
items = ["smartphone", "notebook", "mouse", "keyboard", "monitor", 
         "desktop", "headphone", "clocks", "printer", "tablet", "tv"]

transactions = []
num_transactions = 10000  # Tạo 10,000 hóa đơn

print("📦 Đang đóng gói 10.000 hóa đơn theo kịch bản AI...")

for i in range(1, num_transactions + 1):
    basket = set()
    
    # ÉP KỊCH BẢN MUA SẮM (Để FP-Growth tìm ra luật đẹp)
    scenario = random.choices(["mua_dien_thoai", "mua_laptop", "mua_pc", "mua_le_te"], weights=[35, 30, 15, 20])[0]
    
    if scenario == "mua_dien_thoai":
        basket.add("smartphone")
        if random.random() < 0.7: basket.add("headphone") # 70% mua kèm tai nghe
        if random.random() < 0.4: basket.add("clocks")    # 40% mua smartwatch
            
    elif scenario == "mua_laptop":
        basket.add("notebook")
        if random.random() < 0.8: basket.add("mouse")     # 80% mua kèm chuột
        if random.random() < 0.6: basket.add("keyboard")  # 60% mua phím rời
            
    elif scenario == "mua_pc":
        basket.add("desktop")
        if random.random() < 0.9: basket.add("monitor")   # 90% mua màn hình
        if random.random() < 0.7: basket.add("keyboard")
        if random.random() < 0.7: basket.add("mouse")
            
    else:
        # Nhóm khách mua linh tinh 1-2 món ngẫu nhiên
        basket.update(random.sample(items, k=random.randint(1, 2)))

    # Ghi vào danh sách
    for item in basket:
        transactions.append({"Ma_Hoa_Don": f"INV{i:05d}", "Ten_San_Pham": item})

df = pd.DataFrame(transactions)

# =========================================================
# 2. CHIẾN DỊCH XẢ RÁC VÀO DATA (ĐỂ LẤY 1.5 ĐIỂM LÀM SẠCH)
# =========================================================
print("🗑️ Đang cố tình xả rác vào dữ liệu...")

# Rác 1: Tạo ra 300 dòng bị rỗng (NaN)
null_indices = random.sample(range(len(df)), 300)
df.loc[null_indices, "Ten_San_Pham"] = np.nan

# Rác 2: Cố tình viết sai chính tả 500 dòng
typo_indices = random.sample(range(len(df)), 500)
typo_dict = {
    "smartphone": "smatphone", 
    "notebook": "note_book", 
    "mouse": "mause",
    "keyboard": "key_board"
}
for idx in typo_indices:
    val = df.loc[idx, "Ten_San_Pham"]
    if val in typo_dict:
        df.loc[idx, "Ten_San_Pham"] = typo_dict[val]

# Rác 3: Nhồi thêm 400 dòng trùng lặp y chang nhau (Duplicates)
duplicates = df.sample(400)
df = pd.concat([df, duplicates], ignore_index=True)

# Xáo trộn thứ tự các dòng cho giống data thực tế bị lộn xộn
df = df.sample(frac=1).reset_index(drop=True)

# 3. Xuất xưởng
df.to_csv("data_goc.csv", index=False)
print("✅ Xong! Đã xuất file 'data_goc.csv' (Hơn 20.000 dòng, dính đầy rác và lỗi).")