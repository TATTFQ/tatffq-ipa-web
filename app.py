import os
import json
import re
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sqlalchemy import create_engine, text

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="TATTFQ Web Survey", layout="wide")

DB_URL = st.secrets.get("SUPABASE_DB_URL", os.getenv("SUPABASE_DB_URL", ""))
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", ""))

if not DB_URL:
    st.error("DB belum dikonfigurasi. Set SUPABASE_DB_URL di Streamlit Secrets / env var.")
    st.stop()

engine = create_engine(DB_URL, pool_pre_ping=True)

LIKERT_PERF = {
    1: "Sangat Tidak Setuju",
    2: "Tidak Setuju",
    3: "Agak Tidak Setuju",
    4: "Agak Setuju",
    5: "Setuju",
    6: "Sangat Setuju",
}
LIKERT_IMP = {
    1: "Sangat Tidak Penting",
    2: "Tidak Penting",
    3: "Agak Tidak Penting",
    4: "Agak Penting",
    5: "Penting",
    6: "Sangat Penting",
}

# =========================
# ITEMS (kode + pernyataan)
# =========================
ITEMS = [
    ("Data & Services Integration", "DSI1",
     "Aplikasi telemedicine memungkinkan informasi terkait telekonsultasi klinis (hasil anamnesis, diagnosis, pemeriksaan fisik, penelaahan hasil pemeriksaan penunjang, anjuran, edukasi, pengobatan, dan/atau rujukan yang diberikan) dapat tercatat secara tepat dalam rekam medis pasien sesuai dengan ketentuan peraturan perundang-undangan"),
    ("Data & Services Integration", "DSI2",
     "Aplikasi telemedicine dapat terhubung dengan sistem informasi atau platform lain, untuk mengirim dan/atau menerima rekam medis pasien"),
    ("Data & Services Integration", "DSI3",
     "Aplikasi telemedicine terhubung dengan fasilitas pelayanan kefarmasian dan/atau fasilitas pelayanan kesehatan sehingga dapat memfasilitasi layanan yang terintegrasi"),
    ("Data & Services Integration", "DSI4",
     "Aplikasi telemedicine dapat terhubung dengan alat medis untuk mengirimkan data tanda vital pasien secara real-time"),
    ("Data & Services Integration", "DSI5",
     "Aplikasi telemedicine menyediakan data penting yang saya perlukan dalam memberikan layanan kesehatan jarak jauh"),

    ("Clinical Decision Support", "CDS1",
     "Aplikasi telemedicine dapat secara otomatis memberikan rekomendasi diagnosis, anjuran, edukasi, dan/atau penatalaksanaan pasien (termasuk pengobatan) kepada dokter berdasarkan data dan hasil pemeriksaan pasien"),
    ("Clinical Decision Support", "CDS2",
     "Aplikasi telemedicine dapat secara otomatis mencegah penulisan resep untuk obat-obat yang dikecualikan dalam peraturan pemerintah; memiliki potensi interaksi dengan obat lainnya; dan/atau tidak sesuai dengan kondisi khusus pasien, seperti alergi, hamil, menyusui, atau kondisi lainnya, sehingga hanya obat yang aman dan sesuai yang dapat diresepkan"),

    ("Clinical Communication", "CCM1",
     "Aplikasi telemedicine dapat memfasilitasi pertukaran informasi antar dokter, seperti informasi mengenai kondisi kesehatan dan/atau hasil pemeriksaan pasien yang dirujuk"),
    ("Clinical Communication", "CCM2",
     "Aplikasi telemedicine dapat memfasilitasi komunikasi antar dokter, misalnya untuk mendiskusikan kondisi, diagnosis, dan/atau rencana pengobatan pasien"),
    ("Clinical Communication", "CCM3",
     "Aplikasi telemedicine memungkinkan saya untuk bertukar informasi dengan pasien, seperti bertukar informasi mengenai kondisi kesehatan dan/atau hasil pemeriksaan pasien"),
    ("Clinical Communication", "CCM4",
     "Aplikasi telemedicine memungkinkan saya untuk berkomunikasi secara langsung dengan pasien melalui pesan teks, panggilan audio, dan/atau panggilan video"),
    ("Clinical Communication", "CCM5",
     "Aplikasi telemedicine memungkinkan pasien untuk memberikan penilaian terhadap layanan dan/atau persetujuan/penolakan terhadap rekomendasi medis yang saya berikan"),

    ("Clinical Task Support", "CTS1",
     "Aplikasi telemedicine memungkinkan saya, sebagai dokter yang berwenang, untuk mengakses, meninjau, dan/atau memperbarui data rekam medis pasien"),
    ("Clinical Task Support", "CTS2",
     "Aplikasi telemedicine memungkinkan saya untuk melakukan anamnesis"),
    ("Clinical Task Support", "CTS3",
     "Aplikasi telemedicine memungkinkan saya untuk melakukan pemeriksaan secara memadai melalui media audio dan/atau visual"),
    ("Clinical Task Support", "CTS4",
     "Aplikasi telemedicine memungkinkan saya untuk melakukan penelaahan hasil pemeriksaan penunjang"),
    ("Clinical Task Support", "CTS5",
     "Aplikasi telemedicine memungkinkan saya untuk memberikan anjuran dan/atau edukasi kepada pasien"),
    ("Clinical Task Support", "CTS6",
     "Aplikasi telemedicine memungkinkan saya untuk melakukan penegakan diagnosis kerja"),
    ("Clinical Task Support", "CTS7",
     "Aplikasi telemedicine memungkinkan saya untuk melakukan penatalaksanaan pasien, termasuk pemberian pengobatan"),
    ("Clinical Task Support", "CTS8",
     "Aplikasi telemedicine memungkinkan saya untuk memberikan resep obat dan/atau alat kesehatan yang hanya dapat digunakan untuk satu kali pelayanan resep (tidak dapat diulang) kepada pasien"),
    ("Clinical Task Support", "CTS9",
     "Aplikasi telemedicine memungkinkan saya memberikan rujukan kepada pasien untuk melakukan pemeriksaan kesehatan lanjutan ke fasilitas pelayanan kesehatan"),
    ("Clinical Task Support", "CTS10",
     "Aplikasi telemedicine memungkinkan saya untuk memberikan surat keterangan sakit kepada pasien"),
    ("Clinical Task Support", "CTS11",
     "Aplikasi telemedicine memungkinkan saya untuk memantau perkembangan kondisi pasien setelah pengobatan diberikan"),

    ("Scheduling & Notification", "SCN1",
     "Aplikasi telemedicine memungkinkan saya untuk mengatur jadwal konsultasi dan/atau follow-up dengan pasien"),
    ("Scheduling & Notification", "SCN2",
     "Aplikasi telemedicine menyediakan notifikasi yang saya butuhkan dalam memberikan layanan kesehatan jarak jauh kepada pasien"),

    ("System Reliability", "SRB1",
     "Aplikasi telemedicine yang saya gunakan dapat diandalkan untuk selalu aktif dan/atau tersedia saat saya membutuhkannya"),
    ("System Reliability", "SRB2",
     "Aplikasi telemedicine yang saya gunakan tidak sering mengalami masalah dan/atau kerusakan sistem yang tidak terduga yang dapat mengganggu saya dalam memberikan layanan kesehatan jarak jauh kepada pasien"),
    ("System Reliability", "SRB3",
     "Jika aplikasi telemedicine sedang mengalami kerusakan dan/atau perawatan sistem, terdapat jaminan bahwa aplikasi dapat digunakan kembali dalam waktu tertentu (misalnya 24 jam)"),

    ("Ease of Use & Support", "EUS1",
     "Aplikasi telemedicine mudah untuk dipelajari dan/atau digunakan"),
    ("Ease of Use & Support", "EUS2",
     "Aplikasi telemedicine menyediakan bantuan bagi pengguna yang mengalami kesulitan dalam dalam menggunakan aplikasi"),

    ("Privacy & Security", "PSC1",
     "Aplikasi telemedicine menyediakan mekanisme verifikasi dan/atau validasi keabsahan pengguna untuk memastikan bahwa hanya individu yang berwenang yang dapat mengakses data"),
    ("Privacy & Security", "PSC2",
     "Aplikasi telemedicine memiliki fitur keamanan yang baik untuk melindungi data dari akses yang tidak sah dan/atau kebocoran data"),

    ("Data Quality & Accessibility", "DQA1",
     "Aplikasi telemedicine menyediakan data yang berkualitas (akurat, mutakhir, dan/atau memiliki tingkat detail yang sesuai) untuk tugas saya memberikan layanan kesehatan jarak jauh kepada pasien"),
    ("Data Quality & Accessibility", "DQA2",
     "Aplikasi telemedicine menyediakan error handling untuk menjaga keakuratan input data"),
    ("Data Quality & Accessibility", "DQA4",
     "Aplikasi telemedicine memungkinkan saya untuk mengakses data yang saya butuhkan dengan mudah"),
    ("Data Quality & Accessibility", "DQA5",
     "Aplikasi telemedicine memungkinkan saya untuk menemukan data tertentu dengan mudah"),
    ("Data Quality & Accessibility", "DQA6",
     "Aplikasi telemedicine menyajikan data dengan makna yang jelas dan/atau mudah untuk diketahui"),
    ("Data Quality & Accessibility", "DQA7",
     "Aplikasi telemedicine menampilkan data yang saya perlukan dalam bentuk yang mudah dibaca dan/atau dimengerti"),
]

ITEM_CODES = [code for _, code, _ in ITEMS]

def group_by_dim(items):
    d = {}
    for dim, code, text_ in items:
        d.setdefault(dim, []).append((code, text_))
    return d

DIMS = group_by_dim(ITEMS)

# =========================
# DB helpers
# =========================
def insert_response(respondent_code, meta, perf_dict, imp_dict):
    with engine.begin() as conn:
        conn.execute(
            text("""
                insert into responses (respondent_code, meta, performance, importance)
                values (:respondent_code, :meta::jsonb, :performance::jsonb, :importance::jsonb)
            """),
            dict(
                respondent_code=respondent_code,
                meta=json.dumps(meta, ensure_ascii=False),
                performance=json.dumps(perf_dict, ensure_ascii=False),
                importance=json.dumps(imp_dict, ensure_ascii=False),
            )
        )

def load_all_responses(limit=5000):
    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                select id, created_at, respondent_code, meta, performance, importance
                from responses
                order by created_at desc
                limit :limit
            """),
            dict(limit=limit)
        ).fetchall()

    records = []
    for r in rows:
        meta = r.meta if isinstance(r.meta, dict) else json.loads(r.meta) if r.meta else {}
        perf = r.performance if isinstance(r.performance, dict) else json.loads(r.performance)
        imp  = r.importance if isinstance(r.importance, dict) else json.loads(r.importance)
        rec = {
            "id": r.id,
            "created_at": pd.to_datetime(r.created_at),
            "respondent_code": r.respondent_code,
            **{f"meta_{k}": v for k, v in meta.items()},
        }
        # flatten perf/imp
        for code in ITEM_CODES:
            rec[f"{code}_Performance"] = perf.get(code, np.nan)
            rec[f"{code}_Importance"]  = imp.get(code, np.nan)
        records.append(rec)

    return pd.DataFrame(records)

def compute_stats_and_ipa(df_flat: pd.DataFrame):
    rows = []
    for code in ITEM_CODES:
        p = pd.to_numeric(df_flat[f"{code}_Performance"], errors="coerce")
        i = pd.to_numeric(df_flat[f"{code}_Importance"], errors="coerce")
        rows.append({
            "Item": code,
            "Performance_min": p.min(skipna=True),
            "Performance_max": p.max(skipna=True),
            "Performance_mean": p.mean(skipna=True),
            "Importance_min": i.min(skipna=True),
            "Importance_max": i.max(skipna=True),
            "Importance_mean": i.mean(skipna=True),
        })
    stats = pd.DataFrame(rows)
    stats["Gap_mean(I-P)"] = stats["Importance_mean"] - stats["Performance_mean"]

    # DATA-CENTERED cutoffs (mean of item means)
    x_cut = stats["Performance_mean"].mean()
    y_cut = stats["Importance_mean"].mean()

    def quadrant(r):
        x, y = r["Performance_mean"], r["Importance_mean"]
        if y >= y_cut and x < x_cut:
            return "I - Concentrate Here"
        elif y >= y_cut and x >= x_cut:
            return "II - Keep Up the Good Work"
        elif y < y_cut and x < x_cut:
            return "III - Low Priority"
        else:
            return "IV - Possible Overkill"

    stats["Quadrant"] = stats.apply(quadrant, axis=1)

    quad_lists = {
        q: stats.loc[stats["Quadrant"] == q, "Item"].tolist()
        for q in ["I - Concentrate Here", "II - Keep Up the Good Work",
                  "III - Low Priority", "IV - Possible Overkill"]
    }

    return stats, x_cut, y_cut, quad_lists

def plot_ipa(stats, x_cut, y_cut):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(stats["Performance_mean"], stats["Importance_mean"])
    for _, r in stats.iterrows():
        ax.text(r["Performance_mean"], r["Importance_mean"], r["Item"], fontsize=9)

    ax.axvline(x_cut)
    ax.axhline(y_cut)
    ax.set_xlabel("Performance (Mean)")
    ax.set_ylabel("Importance (Mean)")
    ax.set_title("IPA Matrix (Data-centered)")
    return fig

# =========================
# SIMPLE ROUTING: Respondent vs Admin
# =========================
st.sidebar.title("Menu")
page = st.sidebar.radio("Pilih halaman", ["Responden", "Admin"])

# ---------------------------------
# RESPONDENT PAGE
# ---------------------------------
if page == "Responden":
    st.title("Kuesioner TATTFQ — Responden")
    st.caption("Pengisian 2 tahap: Performance (Persetujuan) → Importance (Kepentingan). Skala 1–6.")

    if "step" not in st.session_state:
        st.session_state.step = 1
        st.session_state.perf = {}
        st.session_state.imp = {}

    with st.expander("Petunjuk Skala", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Performance (Persetujuan)")
            st.write(pd.DataFrame({"Skor": list(LIKERT_PERF.keys()), "Label": list(LIKERT_PERF.values())}))
        with c2:
            st.subheader("Importance (Kepentingan)")
            st.write(pd.DataFrame({"Skor": list(LIKERT_IMP.keys()), "Label": list(LIKERT_IMP.values())}))

    st.subheader("Informasi singkat (opsional)")
    a, b, c = st.columns(3)
    with a:
        respondent_code = st.text_input("Kode responden (opsional)", placeholder="misal: GD-012 / ITB-05")
    with b:
        experience = st.selectbox("Pengalaman telemedicine (opsional)", ["", "< 6 bulan", "6–12 bulan", "1–2 tahun", "> 2 tahun"])
    with c:
        platform = st.text_input("Platform (opsional)", placeholder="misal: Good Doctor, Halodoc")

    meta = {"experience": experience, "platform": platform}

    st.divider()

    # Step 1: Performance
    if st.session_state.step == 1:
        st.header("Tahap 1 — Performance (Tingkat Persetujuan)")
        st.info("Nilai seberapa Anda setuju bahwa kemampuan/fungsi ini tersedia dan mendukung pekerjaan Anda.")

        for dim, items in DIMS.items():
            st.subheader(dim)
            for code, text_ in items:
                with st.container(border=True):
                    st.markdown(f"**{code}.** {text_}")
                    st.session_state.perf[code] = st.radio(
                        f"{code} — Performance",
                        options=list(LIKERT_PERF.keys()),
                        format_func=lambda x: f"{x} — {LIKERT_PERF[x]}",
                        horizontal=True,
                        key=f"perf_{code}",
                    )
            st.divider()

        if st.button("Lanjut ke Tahap 2 (Importance) ➜", type="primary"):
            st.session_state.step = 2
            st.rerun()

    # Step 2: Importance
    else:
        st.header("Tahap 2 — Importance (Tingkat Kepentingan)")
        st.info("Nilai seberapa penting kemampuan/fungsi ini untuk mendukung tugas Anda dalam layanan kesehatan jarak jauh.")

        for dim, items in DIMS.items():
            st.subheader(dim)
            for code, text_ in items:
                with st.container(border=True):
                    st.markdown(f"**{code}.** {text_}")
                    st.session_state.imp[code] = st.radio(
                        f"{code} — Importance",
                        options=list(LIKERT_IMP.keys()),
                        format_func=lambda x: f"{x} — {LIKERT_IMP[x]}",
                        horizontal=True,
                        key=f"imp_{code}",
                    )
            st.divider()

        left, right = st.columns(2)
        with left:
            if st.button("⬅ Kembali ke Performance"):
                st.session_state.step = 1
                st.rerun()

        with right:
            if st.button("✅ Submit", type="primary"):
                # Validasi minimal: pastikan semua item ada
                missing_p = [k for k in ITEM_CODES if k not in st.session_state.perf]
                missing_i = [k for k in ITEM_CODES if k not in st.session_state.imp]
                if missing_p or missing_i:
                    st.error("Masih ada item yang belum terisi. Mohon lengkapi semua.")
                    st.stop()

                insert_response(
                    respondent_code=respondent_code.strip() if respondent_code else None,
                    meta=meta,
                    perf_dict=st.session_state.perf,
                    imp_dict=st.session_state.imp
                )
                st.success("Terima kasih! Jawaban Anda telah tersimpan.")
                # reset untuk responden berikutnya
                st.session_state.step = 1
                st.session_state.perf = {}
                st.session_state.imp = {}

# ---------------------------------
# ADMIN PAGE
# ---------------------------------
else:
    st.title("Admin Dashboard — TATTFQ")

    pwd = st.text_input("Admin password", type="password")
    if not ADMIN_PASSWORD:
        st.warning("ADMIN_PASSWORD belum diset di Secrets/env. Set dulu agar dashboard aman.")
    if pwd != ADMIN_PASSWORD:
        st.stop()

    df = load_all_responses()
    st.success(f"Total respon tersimpan: {len(df)}")

    tab1, tab2, tab3 = st.tabs(["Ringkasan & IPA", "Raw Data", "Kuadran"])

    with tab1:
        if len(df) == 0:
            st.info("Belum ada data.")
        else:
            stats, x_cut, y_cut, quad_lists = compute_stats_and_ipa(df)

            st.subheader("Cut-off (Data-centered)")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Performance cut-off (mean global)", f"{x_cut:.3f}")
            with c2:
                st.metric("Importance cut-off (mean global)", f"{y_cut:.3f}")

            st.subheader("Statistik per item (min/max/mean) + GAP + Kuadran")
            st.dataframe(stats.sort_values("Gap_mean(I-P)", ascending=False), use_container_width=True)

            st.subheader("Plot IPA (Data-centered)")
            fig = plot_ipa(stats, x_cut, y_cut)
            st.pyplot(fig)

    with tab2:
        st.subheader("Raw responses (flattened)")
        st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True)

    with tab3:
        if len(df) == 0:
            st.info("Belum ada data.")
        else:
            stats, x_cut, y_cut, quad_lists = compute_stats_and_ipa(df)
            st.subheader("Daftar item per kuadran")
            for q, items in quad_lists.items():
                st.markdown(f"### {q}")
                st.write(items if items else ["(kosong)"])
