import os
from datetime import datetime, timezone
import uuid

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit.components.v1 as components

from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.dialects.postgresql import JSONB

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="TATTFQ Web Survey", layout="wide")

DB_URL = st.secrets.get("SUPABASE_DB_URL", os.getenv("SUPABASE_DB_URL", ""))

# --- Admin users (role-based access) ---
# admin_general: bisa lihat semua data
# admin_* lainnya: hanya bisa lihat data sesuai platform yang dinilai
ADMIN_USERS = {
    "admin_general": {"password": "admin123", "platform": None},
    "admin_alodokter": {"password": "admin_alodokter123", "platform": "Alodokter"},
    "admin_gooddoctor": {"password": "admin_gooddoctor123", "platform": "Good Doctor"},
    "admin_halodoc": {"password": "admin_halodoc123", "platform": "Halodoc"},
}

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
    # Data & Services Integration
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

    # Clinical Decision Support
    ("Clinical Decision Support", "CDS1",
     "Aplikasi telemedicine dapat secara otomatis memberikan rekomendasi diagnosis, anjuran, edukasi, dan/atau penatalaksanaan pasien (termasuk pengobatan) kepada dokter berdasarkan data dan hasil pemeriksaan pasien"),
    ("Clinical Decision Support", "CDS2",
     "Aplikasi telemedicine dapat secara otomatis mencegah penulisan resep untuk obat-obat yang dikecualikan dalam peraturan pemerintah; memiliki potensi interaksi dengan obat lainnya; dan/atau tidak sesuai dengan kondisi khusus pasien, seperti alergi, hamil, menyusui, atau kondisi lainnya, sehingga hanya obat yang aman dan sesuai yang dapat diresepkan"),

    # Clinical Communication
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

    # Clinical Task Support
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

    # Scheduling & Notification
    ("Scheduling & Notification", "SCN1",
     "Aplikasi telemedicine memungkinkan saya untuk mengatur jadwal konsultasi dan/atau follow-up dengan pasien"),
    ("Scheduling & Notification", "SCN2",
     "Aplikasi telemedicine menyediakan notifikasi yang saya butuhkan dalam memberikan layanan kesehatan jarak jauh kepada pasien"),

    # System Reliability
    ("System Reliability", "SRB1",
     "Aplikasi telemedicine yang saya gunakan dapat diandalkan untuk selalu aktif dan/atau tersedia saat saya membutuhkannya"),
    ("System Reliability", "SRB2",
     "Aplikasi telemedicine yang saya gunakan tidak sering mengalami masalah dan/atau kerusakan sistem yang tidak terduga yang dapat mengganggu saya dalam memberikan layanan kesehatan jarak jauh kepada pasien"),
    ("System Reliability", "SRB3",
     "Jika aplikasi telemedicine sedang mengalami kerusakan dan/atau perawatan sistem, terdapat jaminan bahwa aplikasi dapat digunakan kembali dalam waktu tertentu (misalnya 24 jam)"),

    # Ease of Use & Support
    ("Ease of Use & Support", "EUS1",
     "Aplikasi telemedicine mudah untuk dipelajari dan/atau digunakan"),
    ("Ease of Use & Support", "EUS2",
     "Aplikasi telemedicine menyediakan bantuan bagi pengguna yang mengalami kesulitan dalam dalam menggunakan aplikasi"),

    # Privacy & Security
    ("Privacy & Security", "PSC1",
     "Aplikasi telemedicine menyediakan mekanisme verifikasi dan/atau validasi keabsahan pengguna untuk memastikan bahwa hanya individu yang berwenang yang dapat mengakses data"),
    ("Privacy & Security", "PSC2",
     "Aplikasi telemedicine memiliki fitur keamanan yang baik untuk melindungi data dari akses yang tidak sah dan/atau kebocoran data"),

    # Data Quality & Accessibility
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
ITEM_TEXT = {code: text_ for _, code, text_ in ITEMS}

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
DIM_NAME_BY_ABBR = {abbr: full for full, abbr in DIM_ABBR.items()}

# =========================
# PROFIL OPTIONS (dropdown)
# =========================
GENDER_OPTS = ["", "Perempuan", "Laki-laki"]
AGE_OPTS = [
    "",
    "<26 tahun",
    "26-30 tahun",
    "31-35 tahun",
    "36-40 tahun",
    "41-45 tahun",
    "46-50 tahun",
    "51-55 tahun",
    "56-60 tahun",
    "61-65 tahun",
    ">65 tahun",
]
SPECIALTY_OPTS = [
    "",
    "Dokter umum",
    "Dokter hewan",
    "Dokter gigi",
    "Dokter spesialis anak",
    "Dokter spesialis kulit dan kelamin",
    "Dokter spesialis penyakit dalam",
    "Dokter spesialis paru",
    "Dokter spesialis THT",
    "Dokter spesialis obstetri dan ginekologi",
    "Dokter spesialis kejiwaan",
    "Dokter spesialis mata",
    "Dokter spesialis saraf",
    "Dokter spesialis gizi klinis",
    "Dokter spesialis jantung dan pembulun darah",
    "Dokter spesialis bedah",
    "Dokter spesialis urologi",
    "Dokter spesialis andrologi",
    "Dokter spesialis ortopedi dan traumatologi",
    "Dokter spesialis rehabilitasi medik dan kedokteran fisik",
    "Dokter spesialis anestesiologi",
    "Dokter spesialis radiologi",
    "Dokter spesialis endokrin",
    "Lainnya",
]
DURATION_OPTS = [
    "",
    "<1 tahun",
    "1-2 tahun",
    "3-4 tahun",
    "5-6 tahun",
    "7-8 tahun",
    "9-10 tahun",
    "11-12 tahun",
    "13-14 tahun",
    "15-16 tahun",
    "> 16 tahun",
]
FREQ_OPTS = [
    "",
    "Setiap hari",
    "4-6 kali per minggu",
    "1-3 kali per minggu",
    "1-3 kali per bulan",
    "4-11 kali per tahun",
    "1-3 kali per tahun",
    "Kurang dari 1 kali per tahun",
]
LAST_USE_OPTS = [
    "",
    "Hari ini",
    "Dalam 1 minggu terakhir",
    "Dalam 1 bulan terakhir",
    "Dalam 3 bulan terakhir",
    "Dalam 6 bulan terakhir",
    "Dalam 1 tahun terakhir",
    "Lebih dari 1 tahun yang lalu",
]

# --- Platform Telemedicine yang akan dinilai (dropdown) ---
PLATFORM_OPTS = ["", "Alodokter", "Good Doctor", "Halodoc"]

# =========================
# UX helpers
# =========================
def _request_scroll_to_top():
    st.session_state._scroll_to_top = True

def _run_scroll_to_top_if_requested():
    if st.session_state.get("_scroll_to_top", False):
        components.html(
            """
            <script>
              setTimeout(function() {
                try { window.scrollTo(0,0); } catch(e) {}
                try { document.documentElement.scrollTop = 0; } catch(e) {}
                try { document.body.scrollTop = 0; } catch(e) {}
                try {
                  const main = window.parent.document.querySelector('section.main');
                  if (main) main.scrollTo(0,0);
                } catch(e) {}
              }, 50);
            </script>
            """,
            height=0,
        )
        st.session_state._scroll_to_top = False

def _ensure_default_radio_state():
    for code in ITEM_CODES:
        st.session_state.setdefault(f"perf_{code}", 1)
        st.session_state.setdefault(f"imp_{code}", 1)

def _sync_dict_from_widget(prefix: str) -> dict:
    out = {}
    for code in ITEM_CODES:
        out[code] = int(st.session_state.get(f"{prefix}_{code}", 1))
    return out

def _hydrate_widget_state_from_answers(prefix: str, answers: dict, force: bool = False):
    answers = answers or {}
    for code in ITEM_CODES:
        key = f"{prefix}_{code}"
        desired = int(answers.get(code, 1))
        if force or key not in st.session_state:
            st.session_state[key] = desired

def _enter_step(step: int):
    st.session_state.step = step
    st.session_state._enter_step = True

def _go_home():
    st.session_state.view = "home"
    _request_scroll_to_top()

def _new_respondent_session():
    # step: 0=profil, 1=performance, 2=importance
    st.session_state.step = 0
    st.session_state.perf = {}
    st.session_state.imp = {}
    st.session_state.confirm_submit = False
    st.session_state.pending_meta = {}
    st.session_state._enter_step = True
    st.session_state.respondent_code = f"TATTFQ-{uuid.uuid4().hex[:10].upper()}"
    st.session_state.respondent_started_at = datetime.now(timezone.utc)
    st.session_state.profile = {
        "gender": "",
        "age": "",
        "specialty": "",
        "specialty_other": "",
        "platform": "",  # <-- platform yang akan dinilai (dropdown)
        "telemedicine_duration": "",
        "telemedicine_frequency": "",
        "telemedicine_last_use": "",
    }
    _request_scroll_to_top()

def _reset_survey_state(go_home: bool = False):
    # reset semua untuk responden
    for code in ITEM_CODES:
        st.session_state[f"perf_{code}"] = 1
        st.session_state[f"imp_{code}"] = 1
    st.session_state.confirm_submit = False
    st.session_state.pending_meta = {}
    st.session_state._enter_step = True
    st.session_state.perf = {}
    st.session_state.imp = {}
    st.session_state.step = 0
    st.session_state.profile = {
        "gender": "",
        "age": "",
        "specialty": "",
        "specialty_other": "",
        "platform": "",  # <-- platform yang akan dinilai (dropdown)
        "telemedicine_duration": "",
        "telemedicine_frequency": "",
        "telemedicine_last_use": "",
    }
    st.session_state.respondent_code = f"TATTFQ-{uuid.uuid4().hex[:10].upper()}"
    st.session_state.respondent_started_at = datetime.now(timezone.utc)
    _request_scroll_to_top()
    if go_home:
        _go_home()

def _request_submit_confirmation(meta: dict):
    st.session_state.pending_meta = meta or {}
    st.session_state.confirm_submit = True

def _cancel_submit_confirmation():
    st.session_state.confirm_submit = False
    _request_scroll_to_top()

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

def _confirm_and_submit():
    # ambil jawaban terakhir importance
    st.session_state.imp = _sync_dict_from_widget("imp")

    # hitung durasi (UTC)
    started = st.session_state.get("respondent_started_at")
    ended = datetime.now(timezone.utc)
    duration_sec = None
    if isinstance(started, datetime):
        duration_sec = (ended - started).total_seconds()

    # gabungkan meta profil + timing
    profile = st.session_state.get("profile", {}) or {}
    specialty_final = profile.get("specialty", "")
    if specialty_final == "Lainnya":
        specialty_final = profile.get("specialty_other", "").strip() or "Lainnya"

    meta = {
        "gender": profile.get("gender", ""),
        "age": profile.get("age", ""),
        "specialty": specialty_final,
        # platform yang dinilai disimpan ke meta_platform (dipakai filter admin)
        "platform": (profile.get("platform", "") or "").strip(),
        "telemedicine_duration": profile.get("telemedicine_duration", ""),
        "telemedicine_frequency": profile.get("telemedicine_frequency", ""),
        "telemedicine_last_use": profile.get("telemedicine_last_use", ""),
        "started_at_utc": started.isoformat() if isinstance(started, datetime) else "",
        "submitted_at_utc": ended.isoformat(),
        "duration_sec": duration_sec,
    }

    insert_response(
        respondent_code=st.session_state.get("respondent_code", "").strip(),
        meta=meta,
        perf_dict=st.session_state.get("perf", {}),
        imp_dict=st.session_state.get("imp", {}),
    )

    # flash message di Home (hindari st.rerun() di callback)
    st.session_state["flash_success"] = "Terima kasih! Jawaban Anda telah tersimpan."
    _reset_survey_state(go_home=True)

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

    stats["Quadrant"] = [
        quadrant(x, y) for x, y in zip(stats["Performance_mean"], stats["Importance_mean"])
    ]

    quad_order = [
        "I - Concentrate Here",
        "II - Keep Up the Good Work",
        "III - Low Priority",
        "IV - Possible Overkill",
    ]
    quad_lists = {q: stats.loc[stats["Quadrant"] == q, "Item"].tolist() for q in quad_order}

    return stats, x_cut, y_cut, quad_lists

def compute_dimension_stats_and_ipa(df_flat: pd.DataFrame):
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

    dim_stats["Quadrant"] = [
        quadrant(x, y) for x, y in zip(dim_stats["Performance_mean"], dim_stats["Importance_mean"])
    ]

    quad_order = [
        "I - Concentrate Here",
        "II - Keep Up the Good Work",
        "III - Low Priority",
        "IV - Possible Overkill",
    ]
    quad_lists = {q: dim_stats.loc[dim_stats["Quadrant"] == q, "Dimension"].tolist() for q in quad_order}

    return dim_stats, x_cut, y_cut, quad_lists

def _plot_iso_diagonal(ax, x_cut, y_cut, xlim, ylim):
    b = y_cut - x_cut
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
    ax.set_aspect("equal", adjustable="box")
    return fig

def _round_df_numeric(df_in: pd.DataFrame, decimals: int = 2) -> pd.DataFrame:
    df_out = df_in.copy()
    num_cols = df_out.select_dtypes(include=["number"]).columns
    if len(num_cols) > 0:
        df_out[num_cols] = df_out[num_cols].round(decimals)
    return df_out

def _build_quadrant_table_from_stats(stats_df: pd.DataFrame, label_col: str, quad_col: str = "Quadrant") -> pd.DataFrame:
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
# APP STATE + ROUTING (HOME / RESPONDEN / ADMIN)
# =========================
if "view" not in st.session_state:
    st.session_state.view = "home"

# init state untuk responden
if "step" not in st.session_state:
    _new_respondent_session()

# init state untuk admin
if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False
if "admin_pwd_attempt" not in st.session_state:
    st.session_state.admin_pwd_attempt = False
if "admin_username" not in st.session_state:
    st.session_state.admin_username = ""
if "admin_platform_scope" not in st.session_state:
    st.session_state.admin_platform_scope = None  # None = semua (admin_general)

_run_scroll_to_top_if_requested()
_ensure_default_radio_state()

def render_home():
    # =========================
    # STYLE (CSS)
    # =========================
    st.markdown(
        """
        <style>
        /* Page padding */
        .block-container { padding-top: 2.2rem; padding-bottom: 2rem; }

        /* Hero title */
        .hero-title {
            font-size: 2.6rem;
            font-weight: 800;
            line-height: 1.12;
            margin-bottom: .4rem;
        }
        .hero-subtitle {
            font-size: 1.05rem;
            opacity: .85;
            margin-bottom: 1.1rem;
        }

        /* Cards */
        .card {
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.03);
            border-radius: 18px;
            padding: 18px 18px 14px 18px;
            box-shadow: 0 6px 22px rgba(0,0,0,0.10);
        }
        .card h3 {
            margin: 0 0 .25rem 0;
            font-size: 1.25rem;
        }
        .card p {
            margin: 0;
            opacity: .85;
            font-size: .96rem;
        }

        /* Make buttons bigger */
        div.stButton > button {
            height: 3.05rem;
            border-radius: 14px;
            font-weight: 700;
            width: 100%;
        }

        /* Small badges */
        .badge {
            display: inline-block;
            padding: .25rem .55rem;
            border-radius: 999px;
            font-size: .78rem;
            font-weight: 700;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
            margin-right: .35rem;
        }

        /* Divider spacing */
        hr { margin: 1.2rem 0; }

        /* Footer */
        .footer {
            opacity: .7;
            font-size: .9rem;
            margin-top: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # =========================
    # HERO (Title + Subtitle)
    # =========================
    st.markdown(
        """
        <div class="hero-title">Telemedicine Application Task–Technology Fit Questionnaire (TATTFQ)</div>
        <div class="hero-subtitle">
            Survei singkat untuk menilai kesesuaian tugas klinis dengan fitur/teknologi aplikasi telemedicine,
            dari perspektif <b>physician</b>.
        </div>
        """,
        unsafe_allow_html=True
    )

    # =========================
    # HERO IMAGE (via URL)
    # =========================
    HERO_IMG_URL = "https://images.unsplash.com/photo-1580281657527-47f249e8f8a3?auto=format&fit=crop&w=1600&q=80"
    st.image(HERO_IMG_URL, use_container_width=True)

    # =========================
    # FLASH MESSAGE (after submit)
    # =========================
    if st.session_state.get("flash_success"):
        st.success(st.session_state["flash_success"])
        del st.session_state["flash_success"]

    # =========================
    # FEATURE BADGES
    # =========================
    st.markdown(
        """
        <span class="badge">📌 Importance vs Performance</span>
        <span class="badge">📊 Otomatis min/max/mean</span>
        <span class="badge">🧮 Gap (P−I)</span>
        <span class="badge">🔐 Admin role-based</span>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    # =========================
    # ROLE CARDS + BUTTONS
    # =========================
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown(
            """
            <div class="card">
                <h3>👤 Responden</h3>
                <p>Isi profil singkat, lalu jawab <b>Performance</b> & <b>Importance</b> untuk setiap item.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Mulai Mengisi Kuesioner", type="primary"):
            st.session_state.view = "respondent"
            _new_respondent_session()
            _request_scroll_to_top()
            st.rerun()

    with c2:
        st.markdown(
            """
            <div class="card">
                <h3>🔐 Admin</h3>
                <p>Lihat ringkasan, tabel statistik, kuadran IPA, profil responden, dan raw data.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Masuk Admin Dashboard", type="secondary"):
            st.session_state.view = "admin_login"
            st.session_state.admin_pwd_attempt = False
            _request_scroll_to_top()
            st.rerun()

    st.divider()

    # =========================
    # EXTRA INFO SECTION
    # =========================
    st.subheader("Petunjuk singkat")
    st.markdown(
        """
        - Kuesioner terdiri dari **3 tahap**: Profil → Performance → Importance.  
        - Skala menggunakan **Likert 1–6** (tanpa nilai tengah) agar lebih jelas preferensinya.  
        - Setelah submit, data otomatis direkap untuk **IPA (data-centered)** dan statistik per item/dimensi.
        """
    )

    st.markdown(
        """
        <div class="footer">
            © TATTFQ Survey • Dibuat dengan Streamlit • Data tersimpan di database
        </div>
        """,
        unsafe_allow_html=True
    )

def render_respondent():
    st.title("Kuesioner TATTFQ — Responden")

    if st.button("⬅ Kembali ke Halaman Utama"):
        _go_home()
        st.rerun()

    # indikator 3 tahap
    step = st.session_state.get("step", 0)  # 0 profil, 1 perf, 2 imp
    st.progress(1/3 if step == 0 else (2/3 if step == 1 else 1.0))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("✅ **Profil**" if step == 0 else "☑️ Profil")
    with c2:
        st.markdown("✅ **Performance**" if step == 1 else ("☑️ Performance" if step > 1 else "⏳ **Performance**"))
    with c3:
        st.markdown("✅ **Importance**" if step == 2 else "⏳ **Importance**")

    st.divider()

    # =========================
    # STEP 0: PROFIL
    # =========================
    if step == 0:
        st.header("Tahap 1 — Profil Responden")

        prof = st.session_state.get("profile", {}) or {}

        a, b = st.columns(2)
        with a:
            gender = st.selectbox("Jenis kelamin", GENDER_OPTS, index=GENDER_OPTS.index(prof.get("gender", "")) if prof.get("gender", "") in GENDER_OPTS else 0)
            age = st.selectbox("Usia", AGE_OPTS, index=AGE_OPTS.index(prof.get("age", "")) if prof.get("age", "") in AGE_OPTS else 0)
        with b:
            specialty = st.selectbox("Bidang spesialisasi", SPECIALTY_OPTS, index=SPECIALTY_OPTS.index(prof.get("specialty", "")) if prof.get("specialty", "") in SPECIALTY_OPTS else 0)
            specialty_other = ""
            if specialty == "Lainnya":
                specialty_other = st.text_input("Lainnya (isi bidang spesialisasi)", value=prof.get("specialty_other", ""))

        # --- CHANGED: platform jadi dropdown + label baru ---
        platform = st.selectbox(
            "Aplikasi/Platform Telemedicine yang akan dinilai",
            PLATFORM_OPTS,
            index=PLATFORM_OPTS.index(prof.get("platform", "")) if prof.get("platform", "") in PLATFORM_OPTS else 0
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            tele_dur = st.selectbox(
                "Lama menggunakan aplikasi telemedicine untuk memberikan layanan kesehatan jarak jauh kepada pasien",
                DURATION_OPTS,
                index=DURATION_OPTS.index(prof.get("telemedicine_duration", "")) if prof.get("telemedicine_duration", "") in DURATION_OPTS else 0
            )
        with c2:
            tele_freq = st.selectbox(
                "Frekuensi menggunakan aplikasi telemedicine untuk memberikan layanan kesehatan jarak jauh kepada pasien",
                FREQ_OPTS,
                index=FREQ_OPTS.index(prof.get("telemedicine_frequency", "")) if prof.get("telemedicine_frequency", "") in FREQ_OPTS else 0
            )
        with c3:
            tele_last = st.selectbox(
                "Terakhir kali menggunakan aplikasi telemedicine untuk memberikan layanan kesehatan jarak jauh kepada pasien",
                LAST_USE_OPTS,
                index=LAST_USE_OPTS.index(prof.get("telemedicine_last_use", "")) if prof.get("telemedicine_last_use", "") in LAST_USE_OPTS else 0
            )

        # simpan ke session
        st.session_state.profile = {
            "gender": gender,
            "age": age,
            "specialty": specialty,
            "specialty_other": specialty_other,
            "platform": platform,  # <-- dropdown value
            "telemedicine_duration": tele_dur,
            "telemedicine_frequency": tele_freq,
            "telemedicine_last_use": tele_last,
        }

        # validasi minimal (dropdown wajib dipilih)
        missing = []
        if not gender: missing.append("Jenis kelamin")
        if not age: missing.append("Usia")
        if not specialty: missing.append("Bidang spesialisasi")
        if specialty == "Lainnya" and not specialty_other.strip(): missing.append("Spesialisasi (Lainnya)")
        if not platform: missing.append("Aplikasi/Platform Telemedicine yang akan dinilai")
        if not tele_dur: missing.append("Lama menggunakan telemedicine")
        if not tele_freq: missing.append("Frekuensi telemedicine")
        if not tele_last: missing.append("Terakhir menggunakan telemedicine")

        if missing:
            st.info("Lengkapi dulu: " + ", ".join(missing))

        if st.button("Lanjut ke Tahap 2 (Performance) ➜", type="primary", disabled=bool(missing)):
            _enter_step(1)
            _request_scroll_to_top()
            st.rerun()

    # =========================
    # STEP 1: PERFORMANCE
    # =========================
    elif step == 1:
        if st.session_state.get("_enter_step", False):
            if st.session_state.get("perf"):
                _hydrate_widget_state_from_answers("perf", st.session_state["perf"], force=True)
            st.session_state._enter_step = False

        st.header("Tahap 2 — Performance (Tingkat Persetujuan)")
        st.info("Nilai seberapa Anda setuju bahwa kemampuan/fungsi ini tersedia dan mendukung pekerjaan Anda.")

        for dim, items in DIMS.items():
            st.subheader(dim)
            for code, text_ in items:
                with st.container(border=True):
                    st.markdown(f"**{code}.** {text_}")
                    val = st.radio(
                        f"{code} — Performance",
                        options=list(LIKERT_PERF.keys()),
                        format_func=lambda x: f"{x} — {LIKERT_PERF[x]}",
                        horizontal=True,
                        key=f"perf_{code}",
                    )
                    st.session_state.perf[code] = int(val)
            st.divider()

        left, right = st.columns(2)
        with left:
            if st.button("⬅ Kembali ke Profil"):
                st.session_state.perf = _sync_dict_from_widget("perf")
                _enter_step(0)
                _request_scroll_to_top()
                st.rerun()
        with right:
            if st.button("Lanjut ke Tahap 3 (Importance) ➜", type="primary"):
                st.session_state.perf = _sync_dict_from_widget("perf")
                _hydrate_widget_state_from_answers("imp", st.session_state.get("imp", {}), force=True)
                _enter_step(2)
                _request_scroll_to_top()
                st.rerun()

    # =========================
    # STEP 2: IMPORTANCE
    # =========================
    else:
        if st.session_state.get("_enter_step", False):
            if st.session_state.get("imp"):
                _hydrate_widget_state_from_answers("imp", st.session_state["imp"], force=True)
            st.session_state._enter_step = False

        st.header("Tahap 3 — Importance (Tingkat Kepentingan)")
        st.info("Nilai seberapa penting kemampuan/fungsi ini untuk mendukung tugas Anda dalam layanan kesehatan jarak jauh.")

        for dim, items in DIMS.items():
            st.subheader(dim)
            for code, text_ in items:
                with st.container(border=True):
                    st.markdown(f"**{code}.** {text_}")
                    val = st.radio(
                        f"{code} — Importance",
                        options=list(LIKERT_IMP.keys()),
                        format_func=lambda x: f"{x} — {LIKERT_IMP[x]}",
                        horizontal=True,
                        key=f"imp_{code}",
                    )
                    st.session_state.imp[code] = int(val)
            st.divider()

        left, right = st.columns(2)
        with left:
            if st.button("⬅ Kembali ke Performance"):
                st.session_state.imp = _sync_dict_from_widget("imp")
                _hydrate_widget_state_from_answers("perf", st.session_state.get("perf", {}), force=True)
                _enter_step(1)
                _request_scroll_to_top()
                st.rerun()

        with right:
            submit_disabled = st.session_state.get("confirm_submit", False)
            if st.button("✅ Submit", type="primary", disabled=submit_disabled):
                st.session_state.imp = _sync_dict_from_widget("imp")
                _request_submit_confirmation(meta={})
                _request_scroll_to_top()
                st.rerun()

        if st.session_state.get("confirm_submit", False):
            st.warning(
                "Yakin ingin submit? Setelah submit, jawaban akan tersimpan dan Anda akan kembali ke halaman utama.",
                icon="⚠️"
            )
            c_yes, c_no = st.columns(2)
            with c_yes:
                st.button("✅ Ya, submit sekarang", type="primary", on_click=_confirm_and_submit)
            with c_no:
                st.button("❌ Tidak, kembali", on_click=_cancel_submit_confirmation)

def render_admin_login():
    st.title("Admin — Login")

    if st.button("⬅ Kembali ke Halaman Utama"):
        _go_home()
        st.rerun()

    # --- CHANGED: username + password, role-based ---
    username = st.text_input("Admin username", value=st.session_state.get("admin_username", ""))
    pwd = st.text_input("Admin password", type="password")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Masuk", type="primary", use_container_width=True):
            st.session_state.admin_pwd_attempt = True

            user = (username or "").strip()
            user_info = ADMIN_USERS.get(user)

            if user_info and pwd == user_info.get("password", ""):
                st.session_state.admin_authed = True
                st.session_state.admin_username = user
                st.session_state.admin_platform_scope = user_info.get("platform", None)  # None = semua
                st.session_state.view = "admin"
                _request_scroll_to_top()
                st.rerun()
            else:
                st.session_state.admin_authed = False
                st.session_state.admin_username = ""
                st.session_state.admin_platform_scope = None
                st.error("Username/password salah! Isi dengan benar!")
    with col2:
        if st.button("Reset", use_container_width=True):
            st.session_state.admin_pwd_attempt = False
            st.session_state.admin_authed = False
            st.session_state.admin_username = ""
            st.session_state.admin_platform_scope = None
            st.rerun()

def render_admin_dashboard():
    st.title("Admin Dashboard — TATTFQ")

    # info scope
    scope_platform = st.session_state.get("admin_platform_scope", None)
    admin_user = st.session_state.get("admin_username", "")
    if scope_platform:
        st.caption(f"Login sebagai: **{admin_user}** (Akses data: **{scope_platform}**)")  # provider admin
    else:
        st.caption(f"Login sebagai: **{admin_user}** (Akses data: **SEMUA platform**)")  # admin_general

    top_left, top_right = st.columns([1, 1])
    with top_left:
        if st.button("⬅ Kembali ke Halaman Utama"):
            st.session_state.admin_authed = False
            st.session_state.admin_username = ""
            st.session_state.admin_platform_scope = None
            _go_home()
            st.rerun()
    with top_right:
        if st.button("🚪 Logout"):
            st.session_state.admin_authed = False
            st.session_state.admin_username = ""
            st.session_state.admin_platform_scope = None
            st.session_state.view = "admin_login"
            _request_scroll_to_top()
            st.rerun()

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

    # --- CHANGED: hanya admin_general yang bisa hapus semua ---
    can_delete_all = (scope_platform is None)

    colA, colB = st.columns([1, 3])
    with colA:
        if st.button("🗑️ Hapus semua data", type="secondary", disabled=not can_delete_all):
            st.session_state.confirm_delete_all = True

    if not can_delete_all:
        st.info("Catatan: Hanya **admin_general** yang dapat menghapus semua data.")

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

    # --- CHANGED: filter data berdasarkan platform untuk admin provider ---
    if scope_platform:
        if "meta_platform" in df.columns:
            df = df[df["meta_platform"].fillna("").astype(str).str.strip() == scope_platform].copy()
        else:
            df = df.iloc[0:0].copy()

    st.success(f"Total respon tersimpan: {len(df)}")

    tab1, tab2, tab3, tab4 = st.tabs(["Ringkasan & IPA", "Raw Data", "Kuadran", "Profil & Durasi"])

    with tab1:
        if len(df) == 0:
            st.info("Belum ada data.")
        else:
            stats, x_cut, y_cut, _ = compute_stats_and_ipa(df)
            dim_stats, dx_cut, dy_cut, _ = compute_dimension_stats_and_ipa(df)

            st.subheader("Cut-off (Data-centered) — Items")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Performance cut-off (mean global)", f"{x_cut:.3f}")
            with c2:
                st.metric("Importance cut-off (mean global)", f"{y_cut:.3f}")

            st.subheader("Statistik per item (min/max/mean) + GAP(P-I) + Kuadran")
            stats_show = _round_df_numeric(stats, 2)
            st.dataframe(stats_show.sort_values("Gap_mean(P-I)", ascending=True), use_container_width=True)

            st.subheader("Plot IPA (Data-centered) — Items")
            fig = plot_ipa_items(stats, x_cut, y_cut, show_iso_diagonal=False)
            st.pyplot(fig)

            st.divider()

            st.subheader("Cut-off (Data-centered) — Dimensions")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Performance cut-off (mean dim)", f"{dx_cut:.3f}")
            with c2:
                st.metric("Importance cut-off (mean dim)", f"{dy_cut:.3f}")

            st.subheader("Statistik per dimensi (min/max/mean) + GAP(P-I) + Kuadran")
            dim_show = _round_df_numeric(dim_stats, 2)
            st.dataframe(dim_show.sort_values("Gap_mean(P-I)", ascending=True), use_container_width=True)

            st.subheader("Plot IPA (Data-centered) — Dimensions")
            fig_dim = plot_ipa_dimensions(dim_stats, dx_cut, dy_cut, show_iso_diagonal=False)
            st.pyplot(fig_dim)

    with tab2:
        st.subheader("Raw responses (flattened)")
        st.caption("Kolom waktu per responden tersedia di: meta_started_at_utc, meta_submitted_at_utc, meta_duration_sec.")
        if len(df) == 0 or "created_at" not in df.columns:
            st.info("Belum ada data.")
            st.dataframe(df, use_container_width=True)
        else:
            st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True)

    with tab3:
        if len(df) == 0:
            st.info("Belum ada data.")
        else:
            stats, _, _, quad_lists = compute_stats_and_ipa(df)
            dim_stats, _, _, dim_quad_lists = compute_dimension_stats_and_ipa(df)

            st.subheader("Daftar item per kuadran (kode: isi item)")
            quad_order = [
                "I - Concentrate Here",
                "II - Keep Up the Good Work",
                "III - Low Priority",
                "IV - Possible Overkill",
            ]
            for q in quad_order:
                st.markdown(f"### {q}")
                items = quad_lists.get(q, [])
                if not items:
                    st.write(["(kosong)"])
                else:
                    pretty = [f"- {code}: {ITEM_TEXT.get(code, '')}" for code in items]
                    st.markdown("\n".join(pretty))

            st.divider()

            st.subheader("Daftar dimensi per kuadran (kode: nama lengkap)")
            for q in quad_order:
                st.markdown(f"### {q}")
                dims = dim_quad_lists.get(q, [])
                if not dims:
                    st.write(["(kosong)"])
                else:
                    pretty = [f"- {abbr}: {DIM_NAME_BY_ABBR.get(abbr, '')}" for abbr in dims]
                    st.markdown("\n".join(pretty))

    with tab4:
        if len(df) == 0:
            st.info("Belum ada data.")
        else:
            st.subheader("Ringkasan Durasi Pengisian (detik)")
            dur = pd.to_numeric(df.get("meta_duration_sec", pd.Series(dtype="float")), errors="coerce")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Min", f"{dur.min(skipna=True):.2f}" if dur.notna().any() else "-")
            with c2:
                st.metric("Max", f"{dur.max(skipna=True):.2f}" if dur.notna().any() else "-")
            with c3:
                st.metric("Rata-rata", f"{dur.mean(skipna=True):.2f}" if dur.notna().any() else "-")

            st.divider()
            st.subheader("Ringkasan Profil Responden")

            def _vc(col):
                s = df.get(col, pd.Series(dtype="object")).fillna("").astype(str)
                s = s[s.str.strip() != ""]
                if s.empty:
                    return pd.DataFrame(columns=["Value", "Count"])
                out = s.value_counts().reset_index()
                out.columns = ["Value", "Count"]
                return out

            cols = [
                ("Jenis kelamin", "meta_gender"),
                ("Usia", "meta_age"),
                ("Bidang spesialisasi", "meta_specialty"),
                ("Platform yang dinilai", "meta_platform"),
                ("Lama menggunakan telemedicine", "meta_telemedicine_duration"),
                ("Frekuensi telemedicine", "meta_telemedicine_frequency"),
                ("Terakhir menggunakan telemedicine", "meta_telemedicine_last_use"),
            ]

            grid = st.columns(2)
            for idx, (title, colname) in enumerate(cols):
                with grid[idx % 2]:
                    st.markdown(f"**{title}**")
                    st.dataframe(_vc(colname), use_container_width=True, height=220)

# =========================
# ROUTING
# =========================
view = st.session_state.view

if view == "home":
    render_home()
elif view == "respondent":
    render_respondent()
elif view == "admin_login":
    render_admin_login()
elif view == "admin":
    if not st.session_state.get("admin_authed", False):
        st.session_state.view = "admin_login"
        st.rerun()
    render_admin_dashboard()
else:
    st.session_state.view = "home"
    st.rerun()
