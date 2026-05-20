from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = ROOT_DIR / "data_goc.csv"


def find_excel_file():
    candidates = [
        ROOT_DIR / "Online Retail.xlsx",
        ROOT_DIR.parent / "Online Retail.xlsx",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "Khong tim thay file 'Online Retail.xlsx'. "
        "Hay dat file trong thu muc DoAn hoac thu muc DA_CK_KPDL."
    )


def convert_real_data():
    source_file = find_excel_file()
    print(f"Dang doc file Excel: {source_file}")

    try:
        df = pd.read_excel(source_file, sheet_name="Online Retail")
    except ImportError as exc:
        if "openpyxl" in str(exc):
            raise ImportError(
                "Thieu thu vien openpyxl de doc file .xlsx. "
                "Hay chay bang moi truong .venv cua project hoac cai: pip install openpyxl"
            ) from exc
        raise
    print(f"Tong so dong goc doc duoc: {len(df):,}")

    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df = df.dropna(subset=["InvoiceNo", "Description"])
    print(f"Sau khi loc don huy va dong loi: {len(df):,} dong")

    description = df["Description"].astype(str).str.upper()
    conditions = [
        description.str.contains("CLOCK|ALARM|TIME", regex=True, na=False),
        description.str.contains("PHONE|MOBILE|CHARGE", regex=True, na=False),
        description.str.contains("BAG|BOX|CASE|ORGANIZER", regex=True, na=False),
        description.str.contains("LIGHT|LAMP|CANDLE", regex=True, na=False),
        description.str.contains("STATIONERY|PAPER|NOTEBOOK|BOOK", regex=True, na=False),
        description.str.contains("CARD|HOLDER|CLIP", regex=True, na=False),
        description.str.contains("TOOL|STAND|REST", regex=True, na=False),
        description.str.contains("CUSHION|MAT|PAD", regex=True, na=False),
        description.str.contains("TOY|GAME|KIDS", regex=True, na=False),
        description.str.contains("BOTTLE|MUG|CUP", regex=True, na=False),
    ]

    choices = [
        "clocks",
        "smartphone",
        "headphone",
        "monitor",
        "notebook",
        "keyboard",
        "desktop",
        "mouse",
        "tv",
        "printer",
    ]

    df["Ten_San_Pham"] = np.select(conditions, choices, default="UNKNOWN")
    df = df[df["Ten_San_Pham"] != "UNKNOWN"].copy()
    df = df.rename(columns={"InvoiceNo": "Ma_Hoa_Don"})

    final_df = df[["Ma_Hoa_Don", "Ten_San_Pham"]].drop_duplicates()
    final_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    print(f"Da xuat file du lieu chuan: {OUTPUT_CSV}")
    print(f"Tong so dong dung cho FP-Growth: {len(final_df):,}")
    print("Cac cot dau ra: Ma_Hoa_Don, Ten_San_Pham")


if __name__ == "__main__":
    convert_real_data()
