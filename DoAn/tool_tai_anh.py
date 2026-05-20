import os
import requests

# 1. Tự động tạo thư mục 'img' nếu chưa có
os.makedirs("img", exist_ok=True)

# 2. Danh sách 64 link ảnh tao đã dọn sẵn cho mày
image_links = {
    "p1": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=600&auto=format&fit=crop&q=60",
    "p2": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&auto=format&fit=crop&q=60",
    "p3": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop&q=60",
    "p4": "https://images.unsplash.com/photo-1678652197831-2d180705cd2c?w=600&auto=format&fit=crop&q=60",
    "p5": "https://images.unsplash.com/photo-1655554378901-abde2d1e2e4e?w=600&auto=format&fit=crop&q=60",
    "p6": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop&q=60",
    "p7": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=60",
    "p8": "https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=600&auto=format&fit=crop&q=60",
    "p9": "https://images.unsplash.com/photo-1546054454-aa26e2b734c7?w=600&auto=format&fit=crop&q=60",
    "p10": "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=600&auto=format&fit=crop&q=60",
    "p11": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=60",
    "p12": "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=60",
    "p13": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop&q=60",
    "p14": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=60",
    "p15": "https://images.unsplash.com/photo-1558756520-22cfe5d382ca?w=600&auto=format&fit=crop&q=60",
    "p16": "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=600&auto=format&fit=crop&q=60",
    "p17": "https://images.unsplash.com/photo-1625842268584-8f3296236761?w=600&auto=format&fit=crop&q=60",
    "p18": "https://images.unsplash.com/photo-1496181130358-f07d58b76c8c?w=600&auto=format&fit=crop&q=60",
    "p19": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=60",
    "p20": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&auto=format&fit=crop&q=60",
    "p21": "https://images.unsplash.com/photo-1586816879360-004f5b0c51e3?w=600&auto=format&fit=crop&q=60",
    "p22": "https://images.unsplash.com/photo-1605773527852-c546a8584ea3?w=600&auto=format&fit=crop&q=60",
    "p23": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=60",
    "p24": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&auto=format&fit=crop&q=60",
    "p25": "https://images.unsplash.com/photo-1586816879360-004f5b0c51e3?w=600&auto=format&fit=crop&q=60",
    "p26": "https://images.unsplash.com/photo-1605773527852-c546a8584ea3?w=600&auto=format&fit=crop&q=60",
    "p27": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=60",
    "p28": "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=600&auto=format&fit=crop&q=60",
    "p29": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&auto=format&fit=crop&q=60",
    "p30": "https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&auto=format&fit=crop&q=60",
    "p31": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=60",
    "p32": "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=600&auto=format&fit=crop&q=60",
    "p33": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&auto=format&fit=crop&q=60",
    "p34": "https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&auto=format&fit=crop&q=60",
    "p35": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=60",
    "p36": "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=60",
    "p37": "https://images.unsplash.com/photo-1551645120-d70bfe84c826?w=600&auto=format&fit=crop&q=60",
    "p38": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=60",
    "p39": "https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=600&auto=format&fit=crop&q=60",
    "p40": "https://images.unsplash.com/photo-1551645120-d70bfe84c826?w=600&auto=format&fit=crop&q=60",
    "p41": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=600&auto=format&fit=crop&q=60",
    "p42": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=60",
    "p43": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=600&auto=format&fit=crop&q=60",
    "p44": "https://images.unsplash.com/photo-1563770660941-20978e870e26?w=600&auto=format&fit=crop&q=60",
    "p45": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=600&auto=format&fit=crop&q=60",
    "p46": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=60",
    "p47": "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&auto=format&fit=crop&q=60",
    "p48": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=600&auto=format&fit=crop&q=60",
    "p49": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=600&auto=format&fit=crop&q=60",
    "p50": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=60",
    "p51": "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=600&auto=format&fit=crop&q=60",
    "p52": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=600&auto=format&fit=crop&q=60",
    "p53": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=60",
    "p54": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=600&auto=format&fit=crop&q=60",
    "p55": "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=600&auto=format&fit=crop&q=60",
    "p56": "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=60",
    "p57": "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=60",
    "p58": "https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=60",
    "p59": "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=600&auto=format&fit=crop&q=60",
    "p60": "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=600&auto=format&fit=crop&q=60",
    "p61": "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=600&auto=format&fit=crop&q=60",
    "p62": "https://images.unsplash.com/photo-1593784991095-a205069470b6?w=600&auto=format&fit=crop&q=60",
    "p63": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=600&auto=format&fit=crop&q=60",
    "p64": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&auto=format&fit=crop&q=60"
}

print("Đang khởi động cỗ máy tải ảnh tự động...")
for pid, url in image_links.items():
    file_path = f"img/{pid}.jpg"
    if os.path.exists(file_path):
        print(f"[{pid}] Đã có sẵn, bỏ qua.")
        continue
        
    try:
        response = requests.get(url, timeout=10)
        # Đã fix lỗi ngu status_size -> status_code
        if response.status_code == 200 or response.ok:
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Tải thành công: {file_path}")
        else:
            print(f"❌ Lỗi tải {pid}: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Lỗi mạng khi tải {pid}: {e}")

print("🎉 XONG! Mày mở folder 'img' ra mà húp thành quả đi!")