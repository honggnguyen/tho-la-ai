#!/usr/bin/env python3
"""Tạo src/data/stats.json từ các file Excel gốc trong raw/ (raw/ KHÔNG nằm trong Git).

Nguyên tắc ẩn danh:
  * Chỉ xuất số đếm / trung bình tổng hợp. Không xuất tên, email, SĐT, link, hoá đơn.
  * Không xuất tiền (tài chính, tài trợ).
  * Nhóm có < MIN_CELL người bị gộp vào "Khác" để khó nhận diện.
  * Không xuất giới tính.
Chạy:  python3 scripts/build_stats.py   (cần: pandas, openpyxl)
"""
import json
import re
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "src" / "data" / "stats.json"
MIN_CELL = 3


def read(name, **kw):
    return pd.read_excel(RAW / name, **kw)


def col(df, needle):
    for c in df.columns:
        if needle.lower() in str(c).lower():
            return c
    raise KeyError(needle)


def channel_bucket(text):
    t = str(text).lower()
    out = []
    if "queer museum" in t or "aqm" in t:
        out.append("Đối tác (AQM)")
    if "fanpage" in t or "thơ là ai" in t or "ig thơ" in t:
        out.append("Fanpage TLA")
    if "bạn bè" in t or "người thân" in t:
        out.append("Bạn bè, người thân")
    if "group" in t:
        out.append("Nhóm cộng đồng thơ")
    return out or ["Khác"]


def channels(series):
    s = series.dropna().astype(str)
    s = s[s.str.strip().str.lower() != "false"]
    n = len(s)
    counts = {}
    for v in s:
        for b in channel_bucket(v):
            counts[b] = counts.get(b, 0) + 1
    return n, merge_small(counts)


def merge_small(counts):
    out, other = {}, 0
    for k, v in counts.items():
        if v < MIN_CELL and k != "Khác":
            other += v
        else:
            out[k] = out.get(k, 0) + v
    if other:
        out["Khác"] = out.get("Khác", 0) + other
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def numeric(series):
    return pd.to_numeric(series, errors="coerce").dropna()


def main():
    stats = {"_note": "Số liệu tổng hợp, đã ẩn danh. Sinh tự động bởi scripts/build_stats.py"}

    # --- Instagram: các mốc từ Campaign.xlsx (cột Instagram) ---
    c = read("campaign.xlsx")
    ig = []
    labels = {"Thơ là ai": "Đêm thơ đầu tiên", "AQM": "Series Nghe–Thấy–Nhau",
              "Chơi giữa mùa trăng": "Chơi giữa mùa trăng", "Nước và mơ": "Nước và mơ",
              "Thơ tân hình th": "Thơ tân hình thức"}
    for _, r in c.iterrows():
        v = pd.to_numeric(r.get("Instagram"), errors="coerce")
        if pd.isna(v):
            continue
        name = str(r["SK"])
        lab = next((l for k, l in labels.items() if name.startswith(k)), None)
        if lab:
            ig.append({"label": lab, "followers": int(v)})
    stats["instagram"] = {"milestones": ig, "latest_followers": 508, "latest_asof": "2026-11",
                          "facebook_followers": 3820}

    # --- Đêm thơ đầu tiên ---
    d = read("dem1_dangky.xlsx")
    n, ch = channels(d[col(d, "biết đến")])
    f = read("dem1_feedback.xlsx")
    rate = numeric(f[col(f, "đánh giá trải nghiệm tổng thể")])
    rate = rate[(rate >= 1) & (rate <= 5)]
    stats["dem1"] = {
        "registrations": int(len(d)),
        "channels_n": n, "channels": ch,
        "rating": {"n": int(len(rate)), "mean": round(float(rate.mean()), 2),
                   "dist": {str(k): int(v) for k, v in rate.value_counts().sort_index().items()}},
    }

    # --- Series Nghe–Thấy–Nhau (đăng ký 2025) ---
    a = read("aqm_dangky_2025.xlsx")
    n, ch = channels(a[col(a, "biết đến")])
    age = a[col(a, "độ tuổi")].astype(str).str.lower()
    under22 = int(age.str.contains("14|18 - 22").sum())
    over22 = int(age.str.contains("trên 22").sum())
    stats["aqm"] = {"registrations": int(len(a)), "channels_n": n, "channels": ch,
                    "age": {"n": under22 + over22, "buckets": {"Đến 22 tuổi": under22, "Trên 22 tuổi": over22}}}

    # --- Workshop "Đưa thơ về mặt đất" (thơ tân hình thức) ---
    t = read("tanhinhthuc_dangky.xlsx")
    n, ch = channels(t[col(t, "biết đến")])
    tf = read("tanhinhthuc_feedback.xlsx")
    tr = numeric(tf[col(tf, "thang điểm")])
    stats["tanhinhthuc"] = {"registrations": int(len(t)), "channels_n": n, "channels": ch,
                            "rating": {"n": int(len(tr)), "mean": round(float(tr.mean()), 2) if len(tr) else None}}

    # --- OMLAS / Echoes of Asia (T0 trước, T1 giữa kỳ) ---
    t0, t1 = read("omlas_T0.xlsx"), read("omlas_T1.xlsx")
    qs = [c for c in t0.columns if re.match(r"Q[1-9]\.", str(c))]
    q1 = [c for c in t1.columns if re.match(r"Q[1-9]\.", str(c))]
    short = ["Mục đích & giá trị lãnh đạo", "Hiểu biết SDGs", "Dẫn dắt nhóm có đạo đức",
             "Nhận diện căng thẳng", "Công cụ tự chăm sóc", "Viết/thơ để xử lý cảm xúc",
             "Diễn giải di sản văn hoá", "Thiết kế dự án cộng đồng", "Dạy lại cho thanh niên địa phương"]
    items = []
    for i, (a_, b_) in enumerate(zip(qs, q1)):
        m0, m1 = numeric(t0[a_]).mean(), numeric(t1[b_]).mean()
        items.append({"id": f"Q{i+1}", "label": short[i], "t0": round(float(m0), 2),
                      "t1": round(float(m1), 2), "delta": round(float(m1 - m0), 2)})

    def hubs(df, needle):
        s = df[col(df, needle)].dropna().astype(str)
        s = s.str.replace(r"\s*\(Lead\)", "", regex=True).str.replace(" Hub", "", regex=False)
        vi = {"Vietnam": "Việt Nam", "Bangladesh": "Bangladesh", "Uzbekistan": "Uzbekistan"}
        return merge_small({vi.get(k, k): int(v) for k, v in s.value_counts().items()})

    stats["omlas"] = {
        "t0_n": int(len(t0)), "t1_n": int(len(t1)),
        "hubs_t0": hubs(t0, "Regional Cohort"), "hubs_t1": hubs(t1, "Regional Cohort"),
        "items": items,
        "caveat": "T0 và T1 là hai nhóm trả lời khác quy mô, chưa ghép cặp: chỉ mang tính tham khảo.",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Đã ghi", OUT)


if __name__ == "__main__":
    main()
