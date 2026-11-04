#!/usr/bin/env python3
"""Tạo src/data/stats.json từ các file Excel gốc trong raw/ (raw/ KHÔNG nằm trong Git).

Nguyên tắc ẩn danh:
  * Chỉ xuất số đếm / trung bình / tỷ lệ tổng hợp. Không xuất tên, email, SĐT, link, hoá đơn.
  * Không xuất tiền (tài chính, tài trợ).
  * Nhóm có < MIN_CELL người bị gộp vào "Khác" để bảo vệ danh tính người trả lời.
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
        out.append("Đối tác (A Queer Museum)")
    if "fanpage" in t or "thơ là ai" in t or "ig thơ" in t:
        out.append("Fanpage / IG Thơ-là-ai?")
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


def classify_major(val):
    t = str(val).lower()
    if any(k in t for k in ["máy tính", "nhân tạo", "công nghệ thông tin", "kĩ thuật", "xây dựng", "sinh học", "tự nhiên"]):
        return "Công nghệ (AI/IT), Kỹ thuật & KHTN"
    if any(k in t for k in ["thiết kế", "đồ họa", "đồ hoạ", "truyền thông", "báo chí", "sự kiện", "giải trí"]):
        return "Thiết kế, Truyền thông & Sự kiện"
    if any(k in t for k in ["kinh tế", "kinh doanh", "quản trị", "ngoại giao", "luật"]):
        return "Kinh tế, Quản trị, Ngoại giao & Luật"
    if any(k in t for k in ["xã hội", "sư phạm", "chuyên văn", "nhân văn", "humanities", "ngôn ngữ", "ngo", "học sinh"]):
        return "KH Xã hội, Nhân văn & Sư phạm"
    return "Y tế, Hàng không, Dịch vụ & Tự do"


def main():
    stats = {"_note": "Số liệu tổng hợp, đã ẩn danh. Sinh tự động bởi scripts/build_stats.py"}

    # --- 1. Mạng xã hội: Instagram & Facebook từ Campaign.xlsx ---
    c = read("campaign.xlsx")
    ig = []
    labels = {
        "Thơ là ai": "Đêm thơ #1 (11/2025)",
        "AQM": "Nghe–Thấy–Nhau (01/2026)",
        "Chơi giữa mùa trăng": "Chơi giữa mùa trăng (04/2026)",
        "Nước và mơ": "Nước và mơ (05/2026)",
        "End hết": "Giữa kỳ (05/2026)",
        "Thơ tân hình th": "Đưa thơ về mặt đất (05/2026)",
    }
    for _, r in c.iterrows():
        v = pd.to_numeric(r.get("Instagram"), errors="coerce")
        if pd.isna(v):
            continue
        name = str(r["SK"])
        lab = next((l for k, l in labels.items() if name.startswith(k)), None)
        if lab:
            ig.append({"label": lab, "followers": int(v)})

    ig_latest = 508
    fb_latest = 3820
    stats["instagram"] = {
        "milestones": ig,
        "latest_followers": ig_latest,
        "latest_asof": "2026-11",
        "growth_pct": round((ig_latest - ig[0]["followers"]) / ig[0]["followers"] * 100),
        "facebook_followers": fb_latest,
        "total_social_followers": ig_latest + fb_latest,
    }

    # --- 2. Đêm thơ đầu tiên (11/2025) ---
    d = read("dem1_dangky.xlsx")
    n_dem1_ch, ch_dem1 = channels(d[col(d, "biết đến")])
    confirmed_dem1 = int((pd.to_numeric(d[col(d, "Xác nhận")], errors="coerce") == 1).sum())
    checkin_dem1 = int((pd.to_numeric(d[col(d, "Chekin")], errors="coerce") == 1).sum())

    f = read("dem1_feedback.xlsx")
    rate = numeric(f[col(f, "đánh giá trải nghiệm tổng thể")])
    rate = rate[(rate >= 1) & (rate <= 5)]

    heard_col = f[col(f, "từng nghe đến thơ diễn xướng")].dropna().astype(str)
    attended_col = f[col(f, "từng tham dự đêm thơ diễn xướng")].dropna().astype(str)
    # Loại trừ 1 dòng trả lời "Mình không đi"
    valid_fb = f[~f.iloc[:, 11].astype(str).str.contains("Mình không đi", case=False, na=False)]
    first_time_n = len(valid_fb)
    first_time_count = int(valid_fb[col(f, "từng tham dự đêm thơ diễn xướng")].astype(str).str.contains("Chưa", case=False).sum())
    voice_count = int(valid_fb[col(f, "cất lên tiếng nói")].astype(str).str.contains("Có|Có", case=False).sum())

    stats["dem1"] = {
        "registrations": int(len(d)),
        "confirmed": confirmed_dem1,
        "checked_in": checkin_dem1,
        "channels_n": n_dem1_ch,
        "channels": ch_dem1,
        "first_time": {
            "n": first_time_n,
            "first_time_count": first_time_count,
            "first_time_pct": round(first_time_count / first_time_n * 100, 1),
            "want_dialogue_count": voice_count,
            "want_dialogue_pct": round(voice_count / first_time_n * 100, 1),
        },
        "rating": {
            "n": int(len(rate)),
            "mean": round(float(rate.mean()), 2),
            "dist": {str(int(k)): int(v) for k, v in rate.value_counts().sort_index().items()},
        },
    }

    # --- 3. Series Nghe–Thấy–Nhau (12/2025 – 01/2026) ---
    a = read("aqm_dangky_2025.xlsx")
    n_aqm_ch, ch_aqm = channels(a[col(a, "biết đến")])
    age_a = a[col(a, "độ tuổi")].astype(str).str.lower()
    under22 = int(age_a.str.contains("14|18 - 22").sum())
    over22 = int(age_a.str.contains("trên 22").sum())

    ev_col = a[col(a, "đăng ký tham gia sự kiện nào")].dropna().astype(str)
    b1_count = int(ev_col.str.contains("Buổi 1").sum())
    b2_count = int(ev_col.str.contains("Buổi 2").sum())
    b3_count = int(ev_col.str.contains("Buổi 3").sum())
    multi_session = int(ev_col.apply(lambda x: sum(k in x for k in ["Buổi 1", "Buổi 2", "Buổi 3"]) >= 2).sum())
    consent_aqm = int(a[col(a, "đồng ý cho chúng mình lưu trữ")].astype(str).str.contains("Đồng ý", case=False).sum())

    stats["aqm"] = {
        "registrations": int(len(a)),
        "total_session_slots": b1_count + b2_count + b3_count,
        "sessions_breakdown": {
            "Buổi 3 · Triển lãm & Trình diễn Thơ Queer (11/01)": b3_count,
            "Buổi 2 · Blackout Poetry Thơ thủ công (28/12)": b2_count,
            "Buổi 1 · Thảo luận Thấu-kính-nhau (14/12)": b1_count,
        },
        "multi_session_count": multi_session,
        "multi_session_pct": round(multi_session / len(a) * 100, 1),
        "archive_consent_pct": round(consent_aqm / len(a) * 100, 1),
        "channels_n": n_aqm_ch,
        "channels": ch_aqm,
        "age": {"n": under22 + over22, "buckets": {"Đến 22 tuổi": under22, "Trên 22 tuổi": over22}},
    }

    # --- 4. Series Chồng chữ (03/2026) ---
    cc = read("chongchu_dangky_2026.xlsx")
    n_cc_ch, ch_cc = channels(cc[col(cc, "biết đến")])
    age_cc = cc[col(cc, "độ tuổi")].dropna().astype(str).str.lower()
    cc_u22 = int(age_cc.str.contains("18 - 22|14").sum())
    cc_o22 = int(age_cc.str.contains("trên 22").sum())
    cc_tickets = int(numeric(cc[col(cc, "Tổng số vé")]).sum())

    stats["chongchu"] = {
        "total_participants": int(len(cc)),
        "form_registrations": int(cc["Dấu thời gian"].dropna().count()),
        "form_tickets": cc_tickets,
        "channels_n": n_cc_ch,
        "channels": ch_cc,
        "age": {"n": cc_u22 + cc_o22, "buckets": {"Trên 22 tuổi": cc_o22, "Đến 22 tuổi": cc_u22}},
    }

    # --- 5. Workshop "Đưa thơ về mặt đất" (05/2026) ---
    t = read("tanhinhthuc_dangky.xlsx")
    n_tht_ch, ch_tht = channels(t[col(t, "biết đến")])
    tf = read("tanhinhthuc_feedback.xlsx")
    tr = numeric(tf[col(tf, "thang điểm")])
    valid_tickets_tht = numeric(t[col(t, "mấy vé")])
    valid_tickets_tht = int(valid_tickets_tht[valid_tickets_tht <= 5].sum())

    stats["tanhinhthuc"] = {
        "registrations": int(len(t)),
        "tickets": valid_tickets_tht,
        "channels_n": n_tht_ch,
        "channels": ch_tht,
        "rating": {"n": int(len(tr)), "mean": round(float(tr.mean()), 2) if len(tr) else None},
    }

    # --- 6. Tổng hợp Kênh truyền thông & Tỷ trọng Fanpage TLA qua thời gian ---
    all_ch_series = pd.concat([
        d[col(d, "biết đến")].dropna(),
        a[col(a, "biết đến")].dropna(),
        cc[col(cc, "biết đến")].dropna(),
        t[col(t, "biết đến")].dropna(),
    ])
    total_ch_n, total_ch_counts = channels(all_ch_series)
    stats["channels_summary"] = {
        "total_respondents": total_ch_n,
        "aggregate": total_ch_counts,
        "fanpage_share_trend": [
            {"event": "Đêm thơ #1 (11/2025)", "n": n_dem1_ch, "pct": round(2 / n_dem1_ch * 100, 1)},
            {"event": "Nghe–Thấy–Nhau (12/2025)", "n": n_aqm_ch, "pct": round(ch_aqm.get("Fanpage / IG Thơ-là-ai?", 0) / n_aqm_ch * 100, 1)},
            {"event": "Đưa thơ về mặt đất (05/2026)", "n": n_tht_ch, "pct": round(ch_tht.get("Fanpage / IG Thơ-là-ai?", 0) / n_tht_ch * 100, 1)},
        ],
    }

    # --- 7. Chân dung người tham dự: Đa dạng ngành học & Độ tuổi tổng hợp ---
    majors_raw = pd.concat([
        f.iloc[:, 5].dropna().astype(str),
        a.iloc[:, 4].dropna().astype(str),
        cc.iloc[:, 12].dropna().astype(str),
    ])
    major_counts = {}
    for m in majors_raw:
        b = classify_major(m)
        major_counts[b] = major_counts.get(b, 0) + 1
    major_sorted = dict(sorted(major_counts.items(), key=lambda kv: -kv[1]))
    non_lit_count = sum(v for k, v in major_sorted.items() if "Xã hội" not in k)

    stats["audience_profile"] = {
        "majors_n": int(len(majors_raw)),
        "non_literature_pct": round(non_lit_count / len(majors_raw) * 100, 1),
        "majors": major_sorted,
        "age_vn_n": under22 + over22 + cc_u22 + cc_o22,
        "age_vn_buckets": {
            "Đến 22 tuổi (Sinh viên / THPT)": under22 + cc_u22,
            "Trên 22 tuổi (Người đi làm / Sau ĐH)": over22 + cc_o22,
        },
    }

    # --- 8. OMLAS · Echoes of Asia (T0, T1 & Champion Recruitment) ---
    t0, t1 = read("omlas_T0.xlsx"), read("omlas_T1.xlsx")
    champ_xl = pd.ExcelFile(RAW / "omlas_champion_2026.xlsx")
    champ_df = champ_xl.parse("Form Responses 1").dropna(how="all")

    qs = [c for c in t0.columns if re.match(r"Q[1-9]\.", str(c))]
    q1 = [c for c in t1.columns if re.match(r"Q[1-9]\.", str(c))]
    short = [
        "Mục đích & giá trị lãnh đạo",
        "Hiểu biết & áp dụng SDGs",
        "Dẫn dắt nhóm có đạo đức",
        "Nhận diện căng thẳng tâm lý",
        "Công cụ tự chăm sóc bản thân",
        "Viết/thơ để xử lý cảm xúc",
        "Diễn giải di sản văn hoá",
        "Thiết kế dự án cộng đồng",
        "Dạy lại cho thanh niên địa phương",
    ]
    items = []
    for i, (a_, b_) in enumerate(zip(qs, q1)):
        m0, m1 = numeric(t0[a_]).mean(), numeric(t1[b_]).mean()
        items.append({
            "id": f"Q{i+1}",
            "label": short[i],
            "t0": round(float(m0), 2),
            "t1": round(float(m1), 2),
            "delta": round(float(m1 - m0), 2),
        })

    def hubs(df, needle):
        s = df[col(df, needle)].dropna().astype(str)
        s = s.str.replace(r"\s*\(Lead\)", "", regex=True).str.replace(" Hub", "", regex=False)
        vi = {"Vietnam": "Việt Nam", "Bangladesh": "Bangladesh", "Uzbekistan": "Uzbekistan", "Pakistan": "Pakistan"}
        return merge_small({vi.get(k, k): int(v) for k, v in s.value_counts().items()})

    # Độ tuổi T0
    age_t0 = t0[col(t0, "Age Bracket")].dropna().astype(str)
    age_t0_map = {
        "18 – 24 tuổi": int((age_t0 == "18 - 24 years old").sum()),
        "25 – 30 tuổi": int((age_t0 == "25 - 30 years old").sum()),
        "Khác (<18 hoặc >30)": int((~age_t0.isin(["18 - 24 years old", "25 - 30 years old"])).sum()),
    }

    # Kinh nghiệm hoạt động xã hội T0
    exp_t0 = t0[col(t0, "Prior Civic Engagement")].dropna().astype(str)
    exp_t0_map = {
        "Thỉnh thoảng tham gia (1–2 dự án ngắn hạn)": int(exp_t0.str.contains("Occasional").sum()),
        "Thủ lĩnh tích cực (Active changemaker)": int(exp_t0.str.contains("Active").sum()),
        "Lần đầu tiên tham gia (First-time participant)": int(exp_t0.str.contains("No prior").sum()),
    }

    # Động lực tham gia T0
    mot_t0 = t0[col(t0, "Primary Motivations")].dropna().astype(str)
    mot_map = {
        "Phát triển lãnh đạo đạo đức & bền vững (Phase 1)": int(mot_t0.str.contains("Phase 1", case=False).sum()),
        "Kỹ năng quản trị để nhân rộng workshop địa phương": int(mot_t0.str.contains("replicate community", case=False).sum()),
        "Chữa lành cảm xúc, giảm căng thẳng & viết thơ (Phase 2 - TLA)": int(mot_t0.str.contains("Tho La Ai", case=False).sum()),
        "Mở rộng mạng lưới xuyên biên giới châu Á": int(mot_t0.str.contains("cross-border", case=False).sum()),
    }

    # Chỉ số sẵn sàng giữa kỳ T1 (Q12, Q13, Q14, Q16)
    q12_s = numeric(t1[col(t1, "Q12.")])
    q13_s = numeric(t1[col(t1, "Q13.")])
    q14_s = numeric(t1[col(t1, "Q14.")])
    q16_s = t1[col(t1, "Q16.")].dropna().astype(str)
    committed_n = int(q16_s.str.contains("Yes", case=False).sum())

    stats["omlas"] = {
        "t0_n": int(len(t0)),
        "t1_n": int(len(t1)),
        "champions_applicants": int(len(champ_df)),
        "champions_selected": 17,
        "hubs_t0": hubs(t0, "Regional Cohort"),
        "hubs_t1": hubs(t1, "Regional Cohort"),
        "age_t0": age_t0_map,
        "experience_t0": exp_t0_map,
        "motivations_t0": mot_map,
        "items": items,
        "midline_readiness": [
            {
                "id": "Q14",
                "label": "Sẵn sàng chuyển từ Suy tưởng sang Sáng tác/Viết thơ",
                "mean": round(float(q14_s.mean()), 2),
                "high_pct": round(float((q14_s >= 4).sum() / len(q14_s) * 100), 1),
            },
            {
                "id": "Q13",
                "label": "Cảm thấy An toàn Tâm lý (Psychological Safety) khi chia sẻ",
                "mean": round(float(q13_s.mean()), 2),
                "high_pct": round(float((q13_s >= 4).sum() / len(q13_s) * 100), 1),
            },
            {
                "id": "Q12",
                "label": "Nắm vững Lý thuyết Thay đổi (Theory of Change) cho cộng đồng",
                "mean": round(float(q12_s.mean()), 2),
                "high_pct": round(float((q12_s >= 4).sum() / len(q12_s) * 100), 1),
            },
        ],
        "commitment_pct": round(committed_n / len(q16_s) * 100, 1),
        "committed_count": committed_n,
        "caveat": "T0 (n = 44) và T1 (n = 23) là hai nhóm trả lời ở hai thời điểm khác quy mô, chưa ghép cặp từng cá nhân: số liệu phản ánh xu hướng chung của lớp học.",
    }

    # --- 9. Tổng hợp Quy mô & Di sản Sáng tác (Impact Overview) ---
    stats["overview"] = {
        "total_registrations_and_surveys": int(len(d) + len(a) + len(cc) + len(t) + len(t0) + len(t1) + len(champ_df)),
        "vn_registrations": int(len(d) + len(a) + len(cc) + len(t)),
        "intl_surveys": int(len(t0) + len(t1) + len(champ_df)),
        "events_completed": 7,
        "poems_archived": 21,
        "audio_tracks": 10,
        "handwritten_manuscripts": 65,
        "event_photos": 178,
        "zine_pages": 60,
        "artists_count": 9,
        "cultural_partners": 6,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Đã ghi", OUT)


if __name__ == "__main__":
    main()
