import os
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="TATTFQ Web Survey", layout="wide")

DB_URL = st.secrets.get("SUPABASE_DB_URL", os.getenv("SUPABASE_DB_URL", ""))
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", os.getenv("ADMIN_PASSWORD", ""))

if not DB_URL:
    st.error("DB belum dikonfigurasi. Set SUPABASE_DB_URL di Streamlit Secrets / env var.")
    st.stop()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=5,
)

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
    # =========================
    # Data & Services Integration
    # =========================
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

    # =========================
    # Clinical Decision Support
    # =========================
    ("Clinical Decision Support", "CDS1",
     "Aplikasi telemedicine dapat secara otomatis memberikan rekomendasi diagnosis, anjuran, edukasi, dan/atau penatalaksanaan pasien (termasuk pengobatan) kepada dokter berdasarkan data dan hasil pemeriksaan pasien"),
    ("Clinical Decision Support", "CDS2",
     "Aplikasi telemedicine dapat secara otomatis mencegah penulisan resep untuk obat-obat yang dikecualikan dalam peraturan pemerintah; memiliki potensi interaksi dengan obat lainnya; dan/atau tidak sesuai dengan kondisi khusus pasien, seperti alergi, hamil, menyusui, atau kondisi lainnya, sehingga hanya obat yang aman dan sesuai yang dapat diresepkan"),

    # =========================
    # Clinical Communication
    # =========================
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

    # =========================
    # Clinical Task Support
    # =========================
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
     "Aplikasi telemedicine memungkinkan saya memberikan rujukan kepada pasien untuk melakukan pemeriksaan kesehatan lanjutan ke fasilitas pelayanan kesehatan"),
    ("Clinical Task Support", "CTS9",
     "Aplikasi telemedicine memungkinkan saya untuk memantau perkembangan kondisi pasien setelah pengobatan diberikan"),

    # =========================
    # Scheduling & Notification
    # =========================
    ("Scheduling & Notification", "SCN1",
     "Aplikasi telemedicine memungkinkan saya untuk mengatur jadwal konsultasi dan/atau follow-up dengan pasien"),
    ("Scheduling & Notification", "SCN2",
     "Aplikasi telemedicine menyediakan notifikasi yang saya butuhkan dalam memberikan layanan kesehatan jarak jauh kepada pasien"),

    # =========================
    # System Reliability
    # =========================
    ("System Reliability", "SRB1",
     "Aplikasi telemedicine yang saya gunakan dapat diandalkan untuk selalu aktif dan/atau tersedia saat saya membutuhkannya"),
    ("System Reliability", "SRB2",
     "Aplikasi telemedicine yang saya gunakan tidak sering mengalami masalah dan/atau kerusakan sistem yang tidak terduga yang dapat mengganggu saya dalam memberikan layanan kesehatan jarak jauh kepada pasien"),
    ("System Reliability", "SRB3",
     "Jika aplikasi telemedicine sedang mengalami kerusakan dan/atau perawatan sistem, terdapat jaminan bahwa aplikasi dapat digunakan kembali dalam waktu tertentu (misalnya 24 jam)"),

    # =========================
    # Ease of Use & Support
    # =========================
    ("Ease of Use & Support", "EUS1",
     "Aplikasi telemedicine mudah untuk dipelajari dan/atau digunakan"),
    ("Ease of Use & Support", "EUS2",
     "Aplikasi telemedicine menyediakan bantuan bagi pengguna yang mengalami kesulitan dalam dalam menggunakan aplikasi"),

    # =========================
    # Privacy & Security
    # =========================
    ("Privacy & Security", "PSC1",
     "Aplikasi telemedicine menyediakan mekanisme verifikasi dan/atau validasi keabsahan pengguna untuk memastikan bahwa hanya individu yang berwenang yang dapat mengakses data"),
    ("Privacy & Security", "PSC2",
     "Aplikasi telemedicine memiliki fitur keamanan yang baik untuk melindungi data dari akses yang tidak sah dan/atau kebocoran data"),

    # =========================
    # Data Quality & Accessibility
    # =========================
    ("Data Quality & Accessibility", "DQA1",
     "Aplikasi telemedicine menyediakan data yang berkualitas (akurat, mutakhir, dan/atau memiliki tingkat detail yang sesuai) untuk tugas saya memberikan layanan kesehatan jarak jauh kepada pasien"),
    ("Data Quality & Accessibility", "DQA2",
     "Aplikasi telemedicine menyediakan error handling untuk menjaga keakuratan input data"),
    ("Data Quality & Accessibility", "DQA3",
     "Aplikasi telemedicine memungkinkan saya untuk mengakses data yang saya butuhkan dengan mudah"),
    ("Data Quality & Accessibility", "DQA4",
     "Aplikasi telemedicine memungkinkan saya untuk menemukan data tertentu dengan mudah"),
    ("Data Quality & Accessibility", "DQA5",
     "Aplikasi telemedicine menyajikan data dengan makna yang jelas dan/atau mudah untuk diketahui"),
    ("Data Quality & Accessibility", "DQA6",
     "Aplikasi telemedicine menampilkan data yang saya perlukan dalam bentuk yang mudah dibaca dan/atau dimengerti"),
]

ITEM_CODES = [code for _, code, _ in ITEMS]


def group_by_dim(items):
    grouped = {}
    for dim, code, text_ in items:
        grouped.setdefault(dim, []).append((code, text_))
    return grouped


DIMS = group_by_dim(ITEMS)

# =========================
# DIMENSION MAPPING (9 dimensi)
# =========================
DIM_ABBR = {
    "Data & Services Integration": "DSI",
    "Clinical Decision Support": "CDS",
    "Clinical Communication": "CCM",
    "Clinical Task Support": "CTS",
    "Scheduling & Notification": "SCN",
    "System Reliability": "SRB",
    "Ease of Use & Support": "EUS",
    "Privacy & Security": "PSC",
    "Data Quality & Accessibility": "DQA",
}
DIM_CODES = {DIM_ABBR[dim]: [code for code, _ in items] for dim, items in DIMS.items()}

# =========================
# DB helpers
# =========================
def insert_response(respondent_code, meta, perf_dict, imp_dict):
    try:
        stmt = text("""
            INSERT INTO responses (respondent_code, meta, performance, importance)
            VALUES (:respondent_code, :meta, :performance, :importance)
        """).bindparams(
            bindparam("meta", type_=JSONB),
            bindparam("performance", type_=JSONB),
            bindparam("importance", type_=JSONB),
        )

        with engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "respondent_code": respondent_code,
                    "meta": meta or {},
                    "performance": perf_dict or {},
                    "importance": imp_dict or {},
                },
            )
    except Exception as e:
        st.error("Gagal menyimpan ke database. Detail error:")
        st.exception(e)
        st.stop()


def load_all_responses(limit=5000):
    try:
        with engine.begin() as conn:
            rows = conn.execute(
                text("""
                    SELECT id, created_at, respondent_code, meta, performance, importance
                    FROM responses
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()
    except Exception as e:
        st.error("Gagal load data dari database. Detail error:")
        st.exception(e)
        st.stop()

    records = []
    for r in rows:
        meta = r.meta or {}
        perf = r.performance or {}
        imp = r.importance or {}

        rec = {
            "id": r.id,
            "created_at": pd.to_datetime(r.created_at),
            "respondent_code": r.respondent_code,
        }

        for k, v in meta.items():
            rec[f"meta_{k}"] = v

        for code in ITEM_CODES:
            rec[f"{code}_Performance"] = perf.get(code, np.nan)
            rec[f"{code}_Importance"] = imp.get(code, np.nan)

        records.append(rec)

    base_cols = ["id", "created_at", "respondent_code"]
    df = pd.DataFrame.from_records(records)

    if df.empty and len(df.columns) == 0:
        df = pd.DataFrame(columns=base_cols)

    for col in base_cols:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")

    return df


def delete_all_responses():
    try:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE responses RESTART IDENTITY"))
    except Exception as e:
        st.error("Gagal menghapus data. Detail error:")
        st.exception(e)
        st.stop()


def _cancel_delete_all():
    st.session_state.confirm_delete_all = False
    st.session_state.delete_confirm_text = ""


def _confirm_delete_all():
    delete_all_responses()
    st.session_state.confirm_delete_all = False
    st.session_state.delete_confirm_text = ""
    st.session_state.delete_all_done = True


# =========================
# STATS + IPA
# =========================
def compute_stats_and_ipa(df_flat: pd.DataFrame):
    def _series(col: str) -> pd.Series:
        return pd.to_numeric(df_flat.get(col, pd.Series(dtype="float")), errors="coerce")

    rows = []
    for code in ITEM_CODES:
        p = _series(f"{code}_Performance")
        i = _series(f"{code}_Importance")
        rows.append(
            {
                "Item": code,
                "Performance_min": p.min(skipna=True),
                "Performance_max": p.max(skipna=True),
                "Performance_mean": p.mean(skipna=True),
                "Importance_min": i.min(skipna=True),
                "Importance_max": i.max(skipna=True),
                "Importance_mean": i.mean(skipna=True),
            }
        )

    stats = pd.DataFrame(rows)
    stats["Gap_mean(P-I)"] = stats["Performance_mean"] - stats["Importance_mean"]

    x_cut = float(stats["Performance_mean"].mean(skipna=True))
    y_cut = float(stats["Importance_mean"].mean(skipna=True))

    def quadrant(x: float, y: float) -> str:
        if pd.isna(x) or pd.isna(y):
            return "NA"
        if y >= y_cut and x < x_cut:
            return "I - Concentrate Here"
        if y >= y_cut and x >= x_cut:
            return "II - Keep Up the Good Work"
        if y < y_cut and x < x_cut:
            return "III - Low Priority"
        return "IV - Possible Overkill"

    stats["Quadrant"] = [quadrant(x, y) for x, y in zip(stats["Performance_mean"], stats["Importance_mean"])]

    quad_order = [
        "I - Concentrate Here",
        "II - Keep Up the Good Work",
        "III - Low Priority",
        "IV - Possible Overkill",
    ]
    quad_lists = {q: stats.loc[stats["Quadrant"] == q, "Item"].tolist() for q in quad_order}

    return stats, x_cut, y_cut, quad_lists


def compute_dimension_stats_and_ipa(df_flat: pd.DataFrame):
    """
    Skor dimensi per responden = rata-rata item dalam dimensi tersebut.
    Lalu dihitung min/max/mean antar responden, gap mean, dan kuadran (data-centered khusus dimensi).
    """
    if df_flat is None or df_flat.empty:
        cols = [
            "Dimension", "Dimension_name", "n_items",
            "Performance_min", "Performance_max", "Performance_mean",
            "Importance_min", "Importance_max", "Importance_mean",
            "Gap_mean(P-I)", "Quadrant",
        ]
        empty_stats = pd.DataFrame(columns=cols)
        return empty_stats, np.nan, np.nan, {q: [] for q in [
            "I - Concentrate Here",
            "II - Keep Up the Good Work",
            "III - Low Priority",
            "IV - Possible Overkill",
        ]}

    rows = []
    for dim_full, abbr in DIM_ABBR.items():
        codes = DIM_CODES.get(abbr, [])
        perf_cols = [f"{c}_Performance" for c in codes]
        imp_cols = [f"{c}_Importance" for c in codes]

        perf_dim = (
            df_flat.reindex(columns=perf_cols)
            .apply(pd.to_numeric, errors="coerce")
            .mean(axis=1, skipna=True)
        )
        imp_dim = (
            df_flat.reindex(columns=imp_cols)
            .apply(pd.to_numeric, errors="coerce")
            .mean(axis=1, skipna=True)
        )

        rows.append(
            {
                "Dimension": abbr,
                "Dimension_name": dim_full,
                "n_items": len(codes),
                "Performance_min": perf_dim.min(skipna=True),
                "Performance_max": perf_dim.max(skipna=True),
                "Performance_mean": perf_dim.mean(skipna=True),
                "Importance_min": imp_dim.min(skipna=True),
                "Importance_max": imp_dim.max(skipna=True),
                "Importance_mean": imp_dim.mean(skipna=True),
            }
        )

    dim_stats = pd.DataFrame(rows)
    dim_stats["Gap_mean(P-I)"] = dim_stats["Performance_mean"] - dim_stats["Importance_mean"]

    x_cut = float(dim_stats["Performance_mean"].mean(skipna=True))
    y_cut = float(dim_stats["Importance_mean"].mean(skipna=True))

    def quadrant(x: float, y: float) -> str:
        if pd.isna(x) or pd.isna(y):
            return "NA"
        if y >= y_cut and x < x_cut:
            return "I - Concentrate Here"
        if y >= y_cut and x >= x_cut:
            return "II - Keep Up the Good Work"
        if y < y_cut and x < x_cut:
            return "III - Low Priority"
        return "IV - Possible Overkill"

    dim_stats["Quadrant"] = [quadrant(x, y) for x, y in zip(dim_stats["Performance_mean"], dim_stats["Importance_mean"])]

    quad_order = [
        "I - Concentrate Here",
        "II - Keep Up the Good Work",
        "III - Low Priority",
        "IV - Possible Overkill",
    ]
    quad_lists = {q: dim_stats.loc[dim_stats["Quadrant"] == q, "Dimension"].tolist() for q in quad_order}

    return dim_stats, x_cut, y_cut, quad_lists


def _plot_iso_diagonal(ax, x_cut, y_cut, xlim, ylim):
    """
    Garis diagonal slope=1 yang melewati titik (x_cut, y_cut):
      y - y_cut = 1*(x - x_cut)  =>  y = x + (y_cut - x_cut)
    Digambar pada rentang yang sesuai limit axis.
    """
    b = y_cut - x_cut  # intercept untuk y = x + b
    x0, x1 = xlim
    y0 = x0 + b
    y1 = x1 + b
    ax.plot([x0, x1], [y0, y1], linestyle="--", linewidth=1.5)


def plot_ipa_items(stats, x_cut, y_cut, show_iso_diagonal=False):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(stats["Performance_mean"], stats["Importance_mean"])
    for _, r in stats.iterrows():
        if pd.isna(r["Performance_mean"]) or pd.isna(r["Importance_mean"]):
            continue
        ax.text(r["Performance_mean"], r["Importance_mean"], r["Item"], fontsize=9)

    ax.axvline(x_cut)
    ax.axhline(y_cut)

    x_vals = stats["Performance_mean"].dropna()
    y_vals = stats["Importance_mean"].dropna()
    if len(x_vals) and len(y_vals):
        pad = 0.2
        ax.set_xlim(float(x_vals.min()) - pad, float(x_vals.max()) + pad)
        ax.set_ylim(float(y_vals.min()) - pad, float(y_vals.max()) + pad)

    if show_iso_diagonal:
        _plot_iso_diagonal(ax, x_cut, y_cut, ax.get_xlim(), ax.get_ylim())
        ax.set_title("IPA Matrix (Data-centered) — Alternatif (Items)")
    else:
        ax.set_title("IPA Matrix (Data-centered) — Items")

    ax.set_xlabel("Performance (Mean)")
    ax.set_ylabel("Importance (Mean)")

    # supaya garis slope=1 tampil sebagai 45° secara visual
    ax.set_aspect("equal", adjustable="box")

    return fig


def plot_ipa_dimensions(dim_stats, x_cut, y_cut, show_iso_diagonal=False):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(dim_stats["Performance_mean"], dim_stats["Importance_mean"])
    for _, r in dim_stats.iterrows():
        if pd.isna(r["Performance_mean"]) or pd.isna(r["Importance_mean"]):
            continue
        ax.text(r["Performance_mean"], r["Importance_mean"], r["Dimension"], fontsize=10)

    ax.axvline(x_cut)
    ax.axhline(y_cut)

    x_vals = dim_stats["Performance_mean"].dropna()
    y_vals = dim_stats["Importance_mean"].dropna()
    if len(x_vals) and len(y_vals):
        pad = 0.2
        ax.set_xlim(float(x_vals.min()) - pad, float(x_vals.max()) + pad)
        ax.set_ylim(float(y_vals.min()) - pad, float(y_vals.max()) + pad)

    if show_iso_diagonal:
        _plot_iso_diagonal(ax, x_cut, y_cut, ax.get_xlim(), ax.get_ylim())
        ax.set_title("IPA Matrix (Data-centered) — Alternatif (Dimensions)")
    else:
        ax.set_title("IPA Matrix (Data-centered) — Dimensions")

    ax.set_xlabel("Performance (Mean)")
    ax.set_ylabel("Importance (Mean)")

    # supaya garis slope=1 tampil sebagai 45° secara visual
    ax.set_aspect("equal", adjustable="box")

    return fig


def _round_df_numeric(df_in: pd.DataFrame, decimals: int = 2) -> pd.DataFrame:
    """Round only numeric columns; keep text columns unchanged."""
    df_out = df_in.copy()
    num_cols = df_out.select_dtypes(include=["number"]).columns
    if len(num_cols) > 0:
        df_out[num_cols] = df_out[num_cols].round(decimals)
    return df_out


def _build_quadrant_table_from_stats(stats_df: pd.DataFrame, label_col: str, quad_col: str = "Quadrant") -> pd.DataFrame:
    """
    Output: one row per quadrant with list of labels (comma-separated).
    """
    quad_order = [
        "I - Concentrate Here",
        "II - Keep Up the Good Work",
        "III - Low Priority",
        "IV - Possible Overkill",
    ]
    rows = []
    for q in quad_order:
        labels = stats_df.loc[stats_df[quad_col] == q, label_col].astype(str).tolist()
        rows.append({"Quadrant": q, "Items": ", ".join(labels) if labels else ""})
    return pd.DataFrame(rows)


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
        experience = st.selectbox(
            "Pengalaman telemedicine (opsional)",
            ["", "< 6 bulan", "6–12 bulan", "1–2 tahun", "> 2 tahun"],
        )
    with c:
        platform = st.text_input("Platform (opsional)", placeholder="misal: Good Doctor, Halodoc")

    meta = {"experience": experience, "platform": platform}

    st.divider()

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
                missing_p = [k for k in ITEM_CODES if k not in st.session_state.perf]
                missing_i = [k for k in ITEM_CODES if k not in st.session_state.imp]
                if missing_p or missing_i:
                    st.error("Masih ada item yang belum terisi. Mohon lengkapi semua.")
                    st.stop()

                insert_response(
                    respondent_code=(respondent_code.strip() if respondent_code else ""),
                    meta=meta,
                    perf_dict=st.session_state.perf,
                    imp_dict=st.session_state.imp,
                )
                st.success("Terima kasih! Jawaban Anda telah tersimpan.")

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

    st.divider()
    st.subheader("Hapus Semua Data")
    st.caption("Aksi ini akan menghapus SEMUA respons di tabel responses dan tidak bisa dibatalkan.")

    if "confirm_delete_all" not in st.session_state:
        st.session_state.confirm_delete_all = False
    if "delete_confirm_text" not in st.session_state:
        st.session_state.delete_confirm_text = ""
    if "delete_all_done" not in st.session_state:
        st.session_state.delete_all_done = False

    if st.session_state.delete_all_done:
        st.success("Semua data berhasil dihapus.")
        st.session_state.delete_all_done = False

    colA, colB = st.columns([1, 3])
    with colA:
        if st.button("🗑️ Hapus semua data", type="secondary"):
            st.session_state.confirm_delete_all = True

    if st.session_state.confirm_delete_all:
        st.warning("Konfirmasi: Anda yakin ingin menghapus SEMUA data respons?", icon="⚠️")

        confirm_text = st.text_input('Ketik "DELETE" untuk konfirmasi', key="delete_confirm_text")
        can_delete = (confirm_text.strip().upper() == "DELETE")

        c1, c2 = st.columns(2)
        with c1:
            st.button(
                "✅ Ya, hapus sekarang",
                type="primary",
                disabled=not can_delete,
                on_click=_confirm_delete_all,
            )
        with c2:
            st.button("❌ Batal", on_click=_cancel_delete_all)

    st.divider()

    df = load_all_responses()
    st.success(f"Total respon tersimpan: {len(df)}")

    tab1, tab2, tab3 = st.tabs(["Ringkasan & IPA", "Raw Data", "Kuadran"])

    with tab1:
        if len(df) == 0:
            st.info("Belum ada data.")
        else:
            stats, x_cut, y_cut, quad_lists = compute_stats_and_ipa(df)
            dim_stats, dx_cut, dy_cut, dim_quad_lists = compute_dimension_stats_and_ipa(df)

            # ----------------------------
            # DOWNLOAD ALL RESULTS
            # ----------------------------
            st.subheader("Download hasil (CSV)")
            cdl1, cdl2, cdl3, cdl4 = st.columns(4)

            raw_csv = df.sort_values("created_at", ascending=False).to_csv(index=False).encode("utf-8-sig")

            stats_show_dl = _round_df_numeric(stats, 2)
            stats_csv = stats_show_dl.to_csv(index=False).encode("utf-8-sig")

            dim_show_dl = _round_df_numeric(dim_stats, 2)
            dim_csv = dim_show_dl.to_csv(index=False).encode("utf-8-sig")

            quad_item_tbl = _build_quadrant_table_from_stats(stats, label_col="Item")
            quad_dim_tbl = _build_quadrant_table_from_stats(dim_stats, label_col="Dimension")
            quad_items_csv = quad_item_tbl.to_csv(index=False).encode("utf-8-sig")
            quad_dims_csv = quad_dim_tbl.to_csv(index=False).encode("utf-8-sig")

            with cdl1:
                st.download_button(
                    "⬇️ Raw Data (CSV)",
                    data=raw_csv,
                    file_name=f"TATTFQ_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
            with cdl2:
                st.download_button(
                    "⬇️ Statistik Item (CSV)",
                    data=stats_csv,
                    file_name=f"TATTFQ_stats_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
            with cdl3:
                st.download_button(
                    "⬇️ Statistik Dimensi (CSV)",
                    data=dim_csv,
                    file_name=f"TATTFQ_stats_dimensions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
            with cdl4:
                st.download_button(
                    "⬇️ Kuadran (CSV)",
                    data=(quad_items_csv + b"\n\n" + quad_dims_csv),
                    file_name=f"TATTFQ_quadrants_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

            st.caption("Catatan: file 'Kuadran (CSV)' berisi 2 bagian: kuadran item lalu kuadran dimensi.")

            st.divider()

            # ----------------------------
            # ITEMS
            # ----------------------------
            st.subheader("Cut-off (Data-centered) — Items")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Performance cut-off (mean global)", f"{x_cut:.3f}")
            with c2:
                st.metric("Importance cut-off (mean global)", f"{y_cut:.3f}")

            st.subheader("Statistik per item (min/max/mean) + GAP(P-I) + Kuadran")
            stats_show = _round_df_numeric(stats, 2)
            st.dataframe(
                stats_show.sort_values("Gap_mean(P-I)", ascending=True),
                use_container_width=True,
            )

            st.subheader("Plot IPA (Data-centered) — Items")
            fig = plot_ipa_items(stats, x_cut, y_cut, show_iso_diagonal=False)
            st.pyplot(fig)

            st.subheader("Plot IPA Alternatif — Items")
            st.caption(
                "Representasi alternatif mengombinasikan kuadran (cut-off = grand mean) dan garis diagonal 45° "
                "(slope = 1) yang melalui titik (grand mean performance, grand mean importance)."
            )
            fig_alt = plot_ipa_items(stats, x_cut, y_cut, show_iso_diagonal=True)
            st.pyplot(fig_alt)

            st.divider()

            # ----------------------------
            # DIMENSIONS
            # ----------------------------
            st.subheader("Cut-off (Data-centered) — Dimensions")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Performance cut-off (mean dim)", f"{dx_cut:.3f}")
            with c2:
                st.metric("Importance cut-off (mean dim)", f"{dy_cut:.3f}")

            st.subheader("Statistik per dimensi (min/max/mean) + GAP(P-I) + Kuadran")
            dim_show = _round_df_numeric(dim_stats, 2)
            st.dataframe(
                dim_show.sort_values("Gap_mean(P-I)", ascending=True),
                use_container_width=True,
            )

            st.subheader("Plot IPA (Data-centered) — Dimensions")
            fig_dim = plot_ipa_dimensions(dim_stats, dx_cut, dy_cut, show_iso_diagonal=False)
            st.pyplot(fig_dim)

            st.subheader("Plot IPA Alternatif — Dimensions")
            st.caption(
                "Representasi alternatif mengombinasikan kuadran (cut-off = grand mean) dan garis diagonal 45° "
                "(slope = 1) yang melalui titik (grand mean performance, grand mean importance)."
            )
            fig_dim_alt = plot_ipa_dimensions(dim_stats, dx_cut, dy_cut, show_iso_diagonal=True)
            st.pyplot(fig_dim_alt)

    with tab2:
        st.subheader("Raw responses (flattened)")
        if len(df) == 0 or "created_at" not in df.columns:
            st.info("Belum ada data.")
            st.dataframe(df, use_container_width=True)
        else:
            st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True)

    with tab3:
        if len(df) == 0:
            st.info("Belum ada data.")
        else:
            stats, x_cut, y_cut, quad_lists = compute_stats_and_ipa(df)
            dim_stats, dx_cut, dy_cut, dim_quad_lists = compute_dimension_stats_and_ipa(df)

            st.subheader("Daftar item per kuadran")
            for q, items in quad_lists.items():
                st.markdown(f"### {q}")
                st.write(items if items else ["(kosong)"])

            st.divider()

            st.subheader("Daftar dimensi per kuadran")
            for q, dims in dim_quad_lists.items():
                st.markdown(f"### {q}")
                st.write(dims if dims else ["(kosong)"])
