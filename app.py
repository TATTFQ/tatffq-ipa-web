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
        "platform": "",
        "telemedicine_duration": "",
        "telemedicine_frequency": "",
        "telemedicine_last_use": "",
    }
    _request_scroll_to_top()


def _reset_survey_state(go_home: bool = False):
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
        "platform": "",
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
        stmt = text(
            """
            INSERT INTO responses (respondent_code, meta, performance, importance)
            VALUES (:respondent_code, :meta, :performance, :importance)
        """
        ).bindparams(
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
    st.session_state.imp = _sync_dict_from_widget("imp")

    started = st.session_state.get("respondent_started_at")
    ended = datetime.now(timezone.utc)
    duration_sec = None
    if isinstance(started, datetime):
        duration_sec = (ended - started).total_seconds()

    profile = st.session_state.get("profile", {}) or {}
    specialty_final = profile.get("specialty", "")
    if specialty_final == "Lainnya":
        specialty_final = profile.get("specialty_other", "").strip() or "Lainnya"

    meta = {
        "gender": profile.get("gender", ""),
        "age": profile.get("age", ""),
        "specialty": specialty_final,
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

    st.session_state["flash_success"] = "Terima kasih! Jawaban Anda telah tersimpan."
    _reset_survey_state(go_home=True)


def load_all_responses(limit=5000):
    try:
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, created_at, respondent_code, meta, performance, importance
                    FROM responses
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
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

        created_at_utc = pd.to_datetime(r.created_at, utc=True, errors="coerce")
        created_at_local = created_at_utc.tz_convert("Asia/Jakarta") if pd.notna(created_at_utc) else pd.NaT

        started_at_utc = pd.to_datetime(meta.get("started_at_utc", ""), utc=True, errors="coerce")
        submitted_at_utc = pd.to_datetime(meta.get("submitted_at_utc", ""), utc=True, errors="coerce")

        started_at_local = started_at_utc.tz_convert("Asia/Jakarta") if pd.notna(started_at_utc) else pd.NaT
        submitted_at_local = submitted_at_utc.tz_convert("Asia/Jakarta") if pd.notna(submitted_at_utc) else pd.NaT

        effective_time_local = submitted_at_local if pd.notna(submitted_at_local) else created_at_local

        rec = {
            "id": r.id,
            "created_at": created_at_utc,
            "respondent_code": r.respondent_code,
            "created_at_utc": created_at_utc,
            "created_at_local": created_at_local,
            "meta_started_at_utc_dt": started_at_utc,
            "meta_submitted_at_utc_dt": submitted_at_utc,
            "meta_started_at_local": started_at_local,
            "meta_submitted_at_local": submitted_at_local,
            "effective_time_local": effective_time_local,
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


def _plot_iso_diagonal(ax, x_cut, y_cut, xlim, ylim, with_endpoints=True):
    """
    Garis diagonal 45°: y = x + b, melewati titik (x_cut, y_cut) -> b = y_cut - x_cut
    """
    b = y_cut - x_cut
    x0, x1 = xlim
    y0 = x0 + b
    y1 = x1 + b

    # clip agar tetap berada di rentang y-limit (biar rapi)
    ymin, ymax = ylim

    pts = []
    # cek titik potong dengan batas-batas kotak plot
    # 1) x = x0 => y = y0
    if ymin <= y0 <= ymax:
        pts.append((x0, y0))
    # 2) x = x1 => y = y1
    if ymin <= y1 <= ymax:
        pts.append((x1, y1))
    # 3) y = ymin => ymin = x + b => x = ymin - b
    xx = ymin - b
    if x0 <= xx <= x1:
        pts.append((xx, ymin))
    # 4) y = ymax => x = ymax - b
    xx = ymax - b
    if x0 <= xx <= x1:
        pts.append((xx, ymax))

    # ambil 2 titik unik paling ujung
    pts = list(dict.fromkeys(pts))
    if len(pts) >= 2:
        # pilih yang paling kiri dan paling kanan (berdasarkan x)
        pts_sorted = sorted(pts, key=lambda t: t[0])
        pA, pB = pts_sorted[0], pts_sorted[-1]
        if with_endpoints:
            ax.plot([pA[0], pB[0]], [pA[1], pB[1]], linestyle="-", linewidth=2.2, marker="o", zorder=2)
        else:
            ax.plot([pA[0], pB[0]], [pA[1], pB[1]], linestyle="-", linewidth=2.2, zorder=2)
    else:
        ax.plot([x0, x1], [y0, y1], linestyle="-", linewidth=2.2)


def _plot_quadrant_lines(ax, x_cut, y_cut, trimmed_like_example=False):
    """
    - Default (Versi 1): axvline & axhline full.
    - Trimmed (Versi 2): hanya gambar:
        * garis vertikal x=x_cut dari bawah sampai y_cut
        * garis horizontal y=y_cut dari x_cut sampai kanan
      sehingga tidak ada garis pembagi kuadran di area atas/kiri diagonal (sesuai contoh).
    """
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()

    if not trimmed_like_example:
        ax.axvline(x_cut, linewidth=1.5, zorder=2)
        ax.axhline(y_cut, linewidth=1.5, zorder=2)
        return

    ax.plot([x_cut, x_cut], [y0, y_cut], linewidth=2.2, marker="o", markevery=[1], zorder=2)
    ax.plot([x_cut, x1], [y_cut, y_cut], linewidth=2.2, marker="o", markevery=[1], zorder=2)


# =========================
# QUADRANT LABELS (AUTO-FIT: kecil + selalu muat dalam kuadran)
# =========================
def _annotate_quadrants(ax, x_cut, y_cut, trimmed_like_example=False):
    """
    Label kuadran:
    - Font kecil
    - Auto-fit (turun ukuran font sampai teks muat dalam area kuadran)
    - Aman untuk versi diagonal + trimmed
    """
    fig = ax.figure

    # --- Helper: convert rect in axes coords -> display pixel rect ---
    def _rect_axes_to_disp(xa0, ya0, xa1, ya1):
        p0 = ax.transAxes.transform((xa0, ya0))
        p1 = ax.transAxes.transform((xa1, ya1))
        x0, y0 = p0
        x1, y1 = p1
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    def _rect_data_to_disp(xd0, yd0, xd1, yd1):
        p0 = ax.transData.transform((xd0, yd0))
        p1 = ax.transData.transform((xd1, yd1))
        x0, y0 = p0
        x1, y1 = p1
        return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)

    # --- Helper: shrink-to-fit text ---
   def _draw_fit_text(x, y, text, rect_disp, transform):
    # Font label kuadran dibuat SERAGAM dan paling kecil
    q_fs = 4
    q_bbox = dict(boxstyle="round,pad=0.08", alpha=0.06, edgecolor="none")

    ax.text(
        x, y, text,
        transform=transform,
        ha="center", va="center",
        fontsize=q_fs,
        fontweight="normal",
        alpha=0.75,
        clip_on=True,
        bbox=q_bbox,
        zorder=6,   # pastikan selalu di atas garis/marker
    )

    # =========================
    # MODE 1: kuadran kotak biasa
    # =========================
    if not trimmed_like_example:
        x_mid = 0.5
        y_mid = 0.5

        _draw_fit_text(
            0.25, 0.75, "Q1\nConcentrate Here",
            _rect_axes_to_disp(0.00, y_mid, x_mid, 1.00),
            transform=ax.transAxes
        )
        _draw_fit_text(
            0.75, 0.75, "Q2\nKeep Up the Good Work",
            _rect_axes_to_disp(x_mid, y_mid, 1.00, 1.00),
            transform=ax.transAxes
        )
        _draw_fit_text(
            0.25, 0.25, "Q3\nLow Priority",
            _rect_axes_to_disp(0.00, 0.00, x_mid, y_mid),
            transform=ax.transAxes
        )
        _draw_fit_text(
            0.75, 0.25, "Q4\nPossible Overkill",
            _rect_axes_to_disp(x_mid, 0.00, 1.00, y_mid),
            transform=ax.transAxes
        )
        return

    # =========================
    # MODE 2: diagonal + trimmed
    # =========================
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    b = y_cut - x_cut

    def y_diag(x):
        return x + b

    mx = 0.05 * (x1 - x0)
    my = 0.05 * (y1 - y0)

    def _safe_rect(xa0, ya0, xa1, ya1):
        xa0, xa1 = min(xa0, xa1), max(xa0, xa1)
        ya0, ya1 = min(ya0, ya1), max(ya0, ya1)
        xa0 = max(x0, xa0); xa1 = min(x1, xa1)
        ya0 = max(y0, ya0); ya1 = min(y1, ya1)
        return xa0, ya0, xa1, ya1

    # ---- Q2 (bawah diagonal, atas horizontal)
    xL = x_cut + mx
    xR = x1 - mx
    yB = y_cut + my
    yU = y_diag(xL) - my

    if yU > yB:
        xa0, ya0, xa1, ya1 = _safe_rect(xL, yB, xR, yU)
        rect = _rect_data_to_disp(xa0, ya0, xa1, ya1)
        _draw_fit_text((xa0 + xa1) / 2, (ya0 + ya1) / 2,
                       "Q2\nKeep Up the Good Work",
                       rect, ax.transData)
    else:
        # fallback: jika area Q2 terlalu tipis, taruh label pada posisi aman (axes coords)
        _draw_fit_text(
            0.75, 0.78,
            "Q2\nKeep Up the Good Work",
            _rect_axes_to_disp(0.50, 0.50, 1.00, 1.00),
            ax.transAxes
        )

    # ---- Q3 (bawah diagonal, kiri vertikal)
    xL = x0 + mx
    xR = x_cut - mx
    yB = y0 + my
    yU = min(y_cut - my, y_diag(xL) - my)
    if xR > xL and yU > yB:
        xa0, ya0, xa1, ya1 = _safe_rect(xL, yB, xR, yU)
        rect = _rect_data_to_disp(xa0, ya0, xa1, ya1)
        _draw_fit_text((xa0+xa1)/2, (ya0+ya1)/2,
                       "Q3\nLow Priority",
                       rect, ax.transData)

    # ---- Q1 (atas diagonal, kiri vertikal)
    xL = x0 + mx
    xR = x_cut - mx
    yB = max(y_cut + my, y_diag(xR) + my)
    yU = y1 - my
    if xR > xL and yU > yB:
        xa0, ya0, xa1, ya1 = _safe_rect(xL, yB, xR, yU)
        rect = _rect_data_to_disp(xa0, ya0, xa1, ya1)
        _draw_fit_text((xa0+xa1)/2, (ya0+ya1)/2,
                       "Q1\nConcentrate Here",
                       rect, ax.transData)

    # ---- Q4 (bawah horizontal)
    xL = x_cut + mx
    xR = x1 - mx
    yB = y0 + my
    yU = y_cut - my
    if xR > xL and yU > yB:
        xa0, ya0, xa1, ya1 = _safe_rect(xL, yB, xR, yU)
        rect = _rect_data_to_disp(xa0, ya0, xa1, ya1)
        _draw_fit_text((xa0+xa1)/2, (ya0+ya1)/2,
                       "Q4\nPossible Overkill",
                       rect, ax.transData)


# =========================
# IPA PLOTS
# =========================
def plot_ipa_items(stats, x_cut, y_cut, show_iso_diagonal=False, trimmed_quadrant_lines=False, title_suffix=""):
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.scatter(stats["Performance_mean"], stats["Importance_mean"])
    for _, r in stats.iterrows():
        if pd.isna(r["Performance_mean"]) or pd.isna(r["Importance_mean"]):
            continue
        ax.text(r["Performance_mean"], r["Importance_mean"], r["Item"], fontsize=8)

    x_vals = stats["Performance_mean"].dropna()
    y_vals = stats["Importance_mean"].dropna()
    if len(x_vals) and len(y_vals):
        pad = 0.2
        ax.set_xlim(float(x_vals.min()) - pad, float(x_vals.max()) + pad)
        ax.set_ylim(float(y_vals.min()) - pad, float(y_vals.max()) + pad)

    # garis pembagi kuadran (full vs trimmed)
    _plot_quadrant_lines(ax, x_cut, y_cut, trimmed_like_example=trimmed_quadrant_lines)

    # diagonal
    if show_iso_diagonal:
        _plot_iso_diagonal(ax, x_cut, y_cut, ax.get_xlim(), ax.get_ylim(), with_endpoints=True)

    # ✅ tambah label kuadran
    _annotate_quadrants(ax, x_cut, y_cut, trimmed_like_example=trimmed_quadrant_lines)

    ax.set_title(f"IPA Matrix (Data-centered) — Items{title_suffix}")
    ax.set_xlabel("Performance (Mean)")
    ax.set_ylabel("Importance (Mean)")
    ax.set_aspect("equal", adjustable="box")
    return fig


def plot_ipa_dimensions(dim_stats, x_cut, y_cut, show_iso_diagonal=False, trimmed_quadrant_lines=False, title_suffix=""):
    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    ax.scatter(dim_stats["Performance_mean"], dim_stats["Importance_mean"])
    for _, r in dim_stats.iterrows():
        if pd.isna(r["Performance_mean"]) or pd.isna(r["Importance_mean"]):
            continue
        ax.text(r["Performance_mean"], r["Importance_mean"], r["Dimension"], fontsize=9)

    x_vals = dim_stats["Performance_mean"].dropna()
    y_vals = dim_stats["Importance_mean"].dropna()
    if len(x_vals) and len(y_vals):
        pad = 0.2
        ax.set_xlim(float(x_vals.min()) - pad, float(x_vals.max()) + pad)
        ax.set_ylim(float(y_vals.min()) - pad, float(y_vals.max()) + pad)

    # garis pembagi kuadran (full vs trimmed)
    _plot_quadrant_lines(ax, x_cut, y_cut, trimmed_like_example=trimmed_quadrant_lines)

    # diagonal
    if show_iso_diagonal:
        _plot_iso_diagonal(ax, x_cut, y_cut, ax.get_xlim(), ax.get_ylim(), with_endpoints=True)

    # ✅ tambah label kuadran
    _annotate_quadrants(ax, x_cut, y_cut, trimmed_like_example=trimmed_quadrant_lines)

    ax.set_title(f"IPA Matrix (Data-centered) — Dimensions{title_suffix}")
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


# =========================
# APP STATE + ROUTING
# =========================
if "view" not in st.session_state:
    st.session_state.view = "home"

if "step" not in st.session_state:
    _new_respondent_session()

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False
if "admin_pwd_attempt" not in st.session_state:
    st.session_state.admin_pwd_attempt = False
if "admin_username" not in st.session_state:
    st.session_state.admin_username = ""
if "admin_platform_scope" not in st.session_state:
    st.session_state.admin_platform_scope = None

_run_scroll_to_top_if_requested()
_ensure_default_radio_state()


def render_home():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2.2rem; padding-bottom: 2rem; }

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

        .card {
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.03);
            border-radius: 18px;
            padding: 18px 18px 14px 18px;
            box-shadow: 0 6px 22px rgba(0,0,0,0.10);
            margin-bottom: 18px;
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

        div.stButton > button {
            height: 3.05rem;
            border-radius: 14px;
            font-weight: 700;
            width: 100%;
        }

        .footer {
            opacity: .7;
            font-size: .9rem;
            margin-top: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="hero-title">
        Telemedicine Application Task–Technology Fit Questionnaire (TATTFQ)
        </div>
        <div class="hero-subtitle">
        Survei singkat untuk menilai task-technology fit aplikasi telemedicine dari perspektif dokter.
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.get("flash_success"):
        st.success(st.session_state["flash_success"])
        del st.session_state["flash_success"]

    st.write("")

    col_left, col_right = st.columns([3, 1.4], gap="large")

    with col_left:
        HERO_IMG_FILE = "hero.png"
        hero_path = os.path.join(os.path.dirname(__file__), HERO_IMG_FILE)

        if os.path.exists(hero_path):
            st.image(hero_path, width=650)
        else:
            st.warning(
                f"Gambar hero tidak ditemukan: {HERO_IMG_FILE}. "
                "Pastikan file berada di folder yang sama dengan app.py."
            )

    with col_right:
        st.markdown(
            """
            <div class="card">
                <h3>👤 Responden</h3>
                <p>Isi profil singkat, lalu jawab <b>Performance</b> & <b>Importance</b>.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Mulai Mengisi Kuesioner", type="primary"):
            st.session_state.view = "respondent"
            _new_respondent_session()
            _request_scroll_to_top()
            st.rerun()

        st.write("")

        st.markdown(
            """
            <div class="card">
                <h3>🔐 Admin</h3>
                <p>Lihat dan analisis hasil survei.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Masuk Admin Dashboard", type="secondary"):
            st.session_state.view = "admin_login"
            st.session_state.admin_pwd_attempt = False
            _request_scroll_to_top()
            st.rerun()

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

    step = st.session_state.get("step", 0)  # 0 profil, 1 perf, 2 imp
    st.progress(1 / 3 if step == 0 else (2 / 3 if step == 1 else 1.0))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("✅ **Profil**" if step == 0 else "☑️ Profil")
    with c2:
        st.markdown("✅ **Performance**" if step == 1 else ("☑️ Performance" if step > 1 else "⏳ **Performance**"))
    with c3:
        st.markdown("✅ **Importance**" if step == 2 else "⏳ **Importance**")

    st.divider()

    if step == 0:
        st.header("Tahap 1 — Profil Responden")

        prof = st.session_state.get("profile", {}) or {}

        a, b = st.columns(2)
        with a:
            gender = st.selectbox(
                "Jenis kelamin",
                GENDER_OPTS,
                index=GENDER_OPTS.index(prof.get("gender", "")) if prof.get("gender", "") in GENDER_OPTS else 0
            )
            age = st.selectbox(
                "Usia",
                AGE_OPTS,
                index=AGE_OPTS.index(prof.get("age", "")) if prof.get("age", "") in AGE_OPTS else 0
            )
        with b:
            specialty = st.selectbox(
                "Bidang spesialisasi",
                SPECIALTY_OPTS,
                index=SPECIALTY_OPTS.index(prof.get("specialty", "")) if prof.get("specialty", "") in SPECIALTY_OPTS else 0
            )
            specialty_other = ""
            if specialty == "Lainnya":
                specialty_other = st.text_input("Lainnya (isi bidang spesialisasi)", value=prof.get("specialty_other", ""))

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

        st.session_state.profile = {
            "gender": gender,
            "age": age,
            "specialty": specialty,
            "specialty_other": specialty_other,
            "platform": platform,
            "telemedicine_duration": tele_dur,
            "telemedicine_frequency": tele_freq,
            "telemedicine_last_use": tele_last,
        }

        missing = []
        if not gender:
            missing.append("Jenis kelamin")
        if not age:
            missing.append("Usia")
        if not specialty:
            missing.append("Bidang spesialisasi")
        if specialty == "Lainnya" and not specialty_other.strip():
            missing.append("Spesialisasi (Lainnya)")
        if not platform:
            missing.append("Aplikasi/Platform Telemedicine yang akan dinilai")
        if not tele_dur:
            missing.append("Lama menggunakan telemedicine")
        if not tele_freq:
            missing.append("Frekuensi telemedicine")
        if not tele_last:
            missing.append("Terakhir menggunakan telemedicine")

        if missing:
            st.info("Lengkapi dulu: " + ", ".join(missing))

        if st.button("Lanjut ke Tahap 2 (Performance) ➜", type="primary", disabled=bool(missing)):
            _enter_step(1)
            _request_scroll_to_top()
            st.rerun()

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
                st.session_state.admin_platform_scope = user_info.get("platform", None)
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

    scope_platform = st.session_state.get("admin_platform_scope", None)
    admin_user = st.session_state.get("admin_username", "")
    if scope_platform:
        st.caption(f"Login sebagai: **{admin_user}** (Akses data: **{scope_platform}**)")
    else:
        st.caption(f"Login sebagai: **{admin_user}** (Akses data: **SEMUA platform**)")

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

    # =========================
    # LOAD + FILTER PLATFORM + FILTER PERIODE
    # =========================
    df_all = load_all_responses()
    df = df_all.copy()

    # Filter platform sesuai role admin
    if scope_platform:
        if "meta_platform" in df.columns:
            df = df[df["meta_platform"].fillna("").astype(str).str.strip() == scope_platform].copy()
        else:
            df = df.iloc[0:0].copy()

    # =========================
    # FILTER PERIODE
    # =========================
    st.subheader("Filter Periode Ringkasan")
    st.caption("Filter ini mempengaruhi semua tab (Ringkasan & IPA, Raw Data, Kuadran, Profil & Durasi).")

    if "admin_filter_mode" not in st.session_state:
        st.session_state.admin_filter_mode = "Semua data"
    if "admin_filter_start" not in st.session_state:
        st.session_state.admin_filter_start = None
    if "admin_filter_end" not in st.session_state:
        st.session_state.admin_filter_end = None

    effective = pd.to_datetime(df.get("effective_time_local", pd.Series(dtype="object")), errors="coerce")
    effective_nonnull = effective.dropna()

    default_start = None
    default_end = None
    if len(effective_nonnull) > 0:
        default_start = effective_nonnull.min().date()
        default_end = effective_nonnull.max().date()

    cF1, cF2, cF3 = st.columns([1.2, 1, 1])
    with cF1:
        mode = st.radio(
            "Mode ringkasan",
            ["Semua data", "Filter periode"],
            horizontal=True,
            index=0 if st.session_state.admin_filter_mode == "Semua data" else 1,
        )
        st.session_state.admin_filter_mode = mode

    start_date = None
    end_date = None

    if mode == "Filter periode":
        with cF2:
            start_date = st.date_input(
                "Dari tanggal",
                value=st.session_state.admin_filter_start or default_start,
            )
        with cF3:
            end_date = st.date_input(
                "Sampai tanggal",
                value=st.session_state.admin_filter_end or default_end,
            )

        st.session_state.admin_filter_start = start_date
        st.session_state.admin_filter_end = end_date

        if start_date and end_date and start_date > end_date:
            st.error("Rentang tanggal tidak valid: 'Dari tanggal' tidak boleh > 'Sampai tanggal'.")
        else:
            if start_date and end_date:
                eff = pd.to_datetime(df.get("effective_time_local", pd.Series(dtype="object")), errors="coerce")
                df = df.copy()
                df["_eff_date"] = eff.dt.date
                df = df[(df["_eff_date"] >= start_date) & (df["_eff_date"] <= end_date)].copy()
                df.drop(columns=["_eff_date"], inplace=True, errors="ignore")
    else:
        st.session_state.admin_filter_start = None
        st.session_state.admin_filter_end = None

    if mode == "Filter periode" and start_date and end_date and (start_date <= end_date):
        st.success(f"Total respon (setelah filter): {len(df)}  — Periode: {start_date} s/d {end_date}")
    else:
        st.success(f"Total respon tersimpan: {len(df)}")

    tab1, tab2, tab3, tab4 = st.tabs(["Ringkasan & IPA", "Raw Data", "Kuadran", "Profil & Durasi"])

    with tab1:
        if len(df) == 0:
            st.info("Belum ada data (atau tidak ada data pada periode terpilih).")
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

            # ✅ VERSI 1: tanpa diagonal
            st.subheader("Plot IPA (Data-centered) — Items (Versi 1: Tanpa diagonal)")
            fig1 = plot_ipa_items(
                stats, x_cut, y_cut,
                show_iso_diagonal=False,
                trimmed_quadrant_lines=False,
                title_suffix=" (Tanpa diagonal)"
            )
            st.pyplot(fig1, use_container_width=True)

            # ✅ VERSI 2: diagonal + garis kuadran trimmed (mirip contoh)
            st.subheader("Plot IPA (Data-centered) — Items (Versi 2: Dengan diagonal 45°)")
            fig2 = plot_ipa_items(
                stats, x_cut, y_cut,
                show_iso_diagonal=True,
                trimmed_quadrant_lines=True,
                title_suffix=" (Dengan diagonal)"
            )
            st.pyplot(fig2, use_container_width=True)

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

            # ✅ VERSI 1: tanpa diagonal
            st.subheader("Plot IPA (Data-centered) — Dimensions (Versi 1: Tanpa diagonal)")
            figd1 = plot_ipa_dimensions(
                dim_stats, dx_cut, dy_cut,
                show_iso_diagonal=False,
                trimmed_quadrant_lines=False,
                title_suffix=" (Tanpa diagonal)"
            )
            st.pyplot(figd1, use_container_width=True)

            # ✅ VERSI 2: diagonal + garis kuadran trimmed
            st.subheader("Plot IPA (Data-centered) — Dimensions (Versi 2: Dengan diagonal 45°)")
            figd2 = plot_ipa_dimensions(
                dim_stats, dx_cut, dy_cut,
                show_iso_diagonal=True,
                trimmed_quadrant_lines=True,
                title_suffix=" (Dengan diagonal)"
            )
            st.pyplot(figd2, use_container_width=True)

    with tab2:
        # ✅ rename + remove caption
        st.subheader("Raw responses")
        if len(df) == 0:
            st.info("Belum ada data (atau tidak ada data pada periode terpilih).")
            st.dataframe(df, use_container_width=True)
        else:
            show = df.copy()

            helper_time_cols = [
                "created_at_utc",
                "created_at_local",
                "meta_started_at_utc_dt",
                "meta_submitted_at_utc_dt",
                "meta_started_at_local",
                "meta_submitted_at_local",
                "effective_time_local",
            ]
            show = show.drop(columns=[c for c in helper_time_cols if c in show.columns], errors="ignore")

            rename_map = {}
            for c in show.columns:
                if c.startswith("meta_"):
                    rename_map[c] = c.replace("meta_", "", 1)
            show = show.rename(columns=rename_map)

            show = show.rename(
                columns={
                    "started_at_utc": "started",
                    "submitted_at_utc": "submitted",
                    "duration_sec": "duration",
                }
            )

            preferred_front = ["respondent_code", "started", "submitted", "duration"]
            preferred_profile = [
                "age",
                "gender",
                "platform",
                "specialty",
                "telemedicine_duration",
                "telemedicine_frequency",
                "telemedicine_last_use",
            ]

            front = [c for c in preferred_front if c in show.columns]
            prof = [c for c in preferred_profile if c in show.columns]
            rest = [c for c in show.columns if c not in (front + prof)]

            show = show[front + prof + rest]

            sort_col = "submitted" if "submitted" in show.columns else ("created_at" if "created_at" in show.columns else None)
            if sort_col:
                show = show.sort_values(sort_col, ascending=False)

            st.dataframe(show, use_container_width=True)

    with tab3:
        if len(df) == 0:
            st.info("Belum ada data (atau tidak ada data pada periode terpilih).")
        else:
            stats, _, _, quad_lists = compute_stats_and_ipa(df)
            dim_stats, _, _, dim_quad_lists = compute_dimension_stats_and_ipa(df)

            # ✅ rename headings
            st.subheader("Daftar item per kuadran")
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

            st.subheader("Daftar dimensi per kuadran")
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
            st.info("Belum ada data (atau tidak ada data pada periode terpilih).")
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

            def _value_counts_df(colname: str) -> pd.DataFrame:
                s = df.get(colname, pd.Series(dtype="object")).fillna("").astype(str)
                s = s[s.str.strip() != ""]
                if s.empty:
                    return pd.DataFrame(columns=["Value", "Count"])
                out = s.value_counts().reset_index()
                out.columns = ["Value", "Count"]
                return out

            def _profile_barh(title: str, colname: str, key_prefix: str):
                counts = _value_counts_df(colname)
                st.markdown(f"**{title}**")

                if counts.empty:
                    st.caption("Tidak ada data.")
                    return

                # chart + download button "di dekat bar chart"
                left, right = st.columns([4.2, 1.2], vertical_alignment="center")

                with left:
                    fig, ax = plt.subplots(figsize=(6.5, 3.2))
                    # supaya rapi: urutkan dari kecil->besar (barh enak dibaca)
                    counts_plot = counts.sort_values("Count", ascending=True)
                    ax.barh(counts_plot["Value"], counts_plot["Count"])
                    ax.set_xlabel("Count")
                    ax.set_ylabel("")
                    ax.set_title("")
                    plt.tight_layout()
                    st.pyplot(fig, use_container_width=True)

                with right:
                    csv_bytes = counts.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇️ Download",
                        data=csv_bytes,
                        file_name=f"{key_prefix}_counts.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

            cols = [
                ("Jenis kelamin", "meta_gender", "gender"),
                ("Usia", "meta_age", "age"),
                ("Bidang spesialisasi", "meta_specialty", "specialty"),
                ("Platform yang dinilai", "meta_platform", "platform"),
                ("Lama menggunakan telemedicine", "meta_telemedicine_duration", "tele_dur"),
                ("Frekuensi telemedicine", "meta_telemedicine_frequency", "tele_freq"),
                ("Terakhir menggunakan telemedicine", "meta_telemedicine_last_use", "tele_last"),
            ]

            grid = st.columns(2)
            for idx, (title, colname, keyp) in enumerate(cols):
                with grid[idx % 2]:
                    _profile_barh(title, colname, keyp)


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
