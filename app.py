import os
import tempfile
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import pandas as pd
import streamlit as st

from gcode_checker import GCodeChecker

# --- YAZICI VERİTABANI ---
PRINTER_DATABASE = {
    "Custom (Manuel / Manual)": (220, 220, 250),
    "Anycubic Kobra 2 / Neo / Pro": (220, 220, 250),
    "Anycubic Kobra 2 Plus": (320, 320, 400),
    "Anycubic Kobra 2 Max": (420, 420, 500),
    "Anycubic i3 Mega / Mega S": (210, 210, 205),
    "Anycubic Vyper": (245, 245, 260),
    "Artillery Sidewinder X1 / X2": (300, 300, 400),
    "Artillery Genius / Genius Pro": (220, 220, 250),
    "Bambu Lab X1 / P1P / P1S / A1": (256, 256, 256),
    "Bambu Lab A1 Mini": (180, 180, 180),
    "Creality Ender-3 / V2 / Pro": (220, 220, 250),
    "Creality Ender-3 S1 / Pro": (220, 220, 270),
    "Creality Ender-3 S1 Plus": (300, 300, 300),
    "Creality Ender-3 V3 SE / KE": (220, 220, 250),
    "Creality Ender-5 Plus": (350, 350, 400),
    "Creality CR-10 / V2 / V3": (300, 300, 400),
    "Creality K1 / K1C": (220, 220, 250),
    "Creality K1 Max": (300, 300, 300),
    "Elegoo Neptune 3 / 4 Pro": (225, 225, 265),
    "Elegoo Neptune 3 / 4 Plus": (320, 320, 385),
    "Elegoo Neptune 3 / 4 Max": (420, 420, 480),
    "Flashforge Adventurer 5M / Pro": (220, 220, 220),
    "FLSun V400": (300, 300, 410),
    "FLSun Super Racer (SR)": (260, 260, 330),
    "Prusa i3 MK3S+ / MK4": (250, 210, 220),
    "Prusa MINI+": (180, 180, 180),
    "Prusa XL": (360, 360, 360),
    "Sovol SV06": (220, 220, 250),
    "Sovol SV06 Plus": (300, 300, 340),
    "Sovol SV08": (350, 350, 345),
    "Voron V0.1 / V0.2": (120, 120, 120),
    "Voron Trident/V2.4 (250)": (250, 250, 250),
    "Voron V2.4 (300)": (300, 300, 300),
    "Voron V2.4 (350)": (350, 350, 350)
}

# --- ARAYÜZ ÇEVİRİ SÖZLÜĞÜ ---
UI = {
    "TR": {
        "title": "G-Code Checker", "desc": "Baskı öncesi hataları ve takım yolunu önceden gör.",
        "settings": "Ayarlar", "printer": "Yazıcı Profili", "fil_set": "Filament Ayarları",
        "dia": "Çap (mm)", "dens": "Yoğunluk", "up": "G-Code Dosyanı Yükle (.gcode)", "wait": "Ayarlarını yap ve G-Code dosyanı yükle...",
        "analyzing": "Analiz ediliyor...", "done": "Analiz Tamamlandı!", 
        "t_sum": "Özet & İstatistikler", "t_prev": "Takım Yolu (XY)", "t_str": "Yapısal Kontrol", "t_err": "Hatalar & Bulgular",
        "time": "Tahmini Süre", "weight": "Ağırlık", "len": "Uzunluk", "layer": "Katman",
        "show_trv": "Travel Hareketlerini Göster", "no_err": "Harika! Dosyada hata bulunamadı.",
        "det_stats": "G-Code İstatistikleri (Detaylı)", "hist": "Hız - Zaman Histogramı", "dl_btn": "Raporu İndir (CSV)",
        "start_checks": "Başlangıç Rutinleri", "end_checks": "Bitiş Rutinleri",
        "axis_stats": "G-Code İstatistikleri (Eksen Bazlı)", "err_title": "Bulgular & Uyarılar",
        "empty_head": "Analiz İçin G-Code Bekleniyor", "empty_desc": "Dosyanı yüklediğinde aşağıdaki kontroller otomatik başlatılır:"
    },
    "EN": {
        "title": "G-Code Checker", "desc": "Catch print errors and preview toolpaths before printing.",
        "settings": "Settings", "printer": "Printer Profile", "fil_set": "Filament Settings",
        "dia": "Diameter (mm)", "dens": "Density", "up": "Upload G-Code File (.gcode)", "wait": "Adjust settings and upload your G-Code...",
        "analyzing": "Analyzing...", "done": "Analysis Complete!", 
        "t_sum": "Summary & Stats", "t_prev": "Toolpath (XY)", "t_str": "Structure", "t_err": "Issues & Findings",
        "time": "Est. Time", "weight": "Weight", "len": "Length", "layer": "Layers",
        "show_trv": "Show Travel Moves", "no_err": "Great! No issues found.",
        "det_stats": "Detailed G-Code Statistics", "hist": "Speed-Time Histogram", "dl_btn": "Download Report (CSV)",
        "start_checks": "Start Routines", "end_checks": "End Routines",
        "axis_stats": "G-Code Statistics Per Axis", "err_title": "Findings & Warnings",
        "empty_head": "Waiting for G-Code", "empty_desc": "When you upload your file, checks will run automatically:"
    }
}

st.set_page_config(page_title="G-Code Checker", page_icon="🖨️", layout="wide", initial_sidebar_state="expanded")

# --- CSS: OKUNABİLİRLİK VE BOŞLUK DÜZENLEMELERİ ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    thead tr th { background-color: #f1f5f9 !important; color: #334155 !important; font-weight: 600 !important; }
    .feat-card { 
        background: white; border: 1px solid #e2e8f0; padding: 15px; 
        border-radius: 10px; border-left: 4px solid #38bdf8; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 10px; 
    }
    .feat-card h4 { margin:0 0 5px 0; font-size: 15px; color: #0f172a; }
    .feat-card p { margin:0; font-size: 13px; opacity: 0.8; color: #64748b; }
</style>
""", unsafe_allow_html=True)

lang_options = {"Türkçe": "TR", "English": "EN"}
sel_lang_name = st.sidebar.selectbox("🌍 Dil / Language", list(lang_options.keys()), index=0)
LANG = lang_options[sel_lang_name]
def t(key): return UI.get(LANG, UI["EN"]).get(key, key)

# --- SİDEBAR ---
with st.sidebar:
    st.markdown(f"## {t('settings')}")
    st.divider()
    p_keys = list(PRINTER_DATABASE.keys())
    p_prof = st.selectbox(t("printer"), p_keys, index=13) # Ender-3 V3 SE index
    def_x, def_y, def_z = PRINTER_DATABASE[p_prof]
    is_cust = p_prof.startswith("Custom")
    cx, cy, cz = st.columns(3)
    bed_x = cx.number_input("X", value=def_x, disabled=not is_cust)
    bed_y = cy.number_input("Y", value=def_y, disabled=not is_cust)
    max_z = cz.number_input("Z", value=def_z, disabled=not is_cust)
    st.divider()
    f_dia = st.number_input(t("dia"), value=1.75, step=0.05, format="%.2f")
    f_type = st.selectbox(t("dens"), ["PLA (1.24)", "PETG (1.27)", "ABS (1.04)", "TPU (1.21)", "Custom"])
    f_dens = st.number_input("Density Val.", value=1.24) if f_type == "Custom" else float(f_type.split("(")[1].split(")")[0])

# --- HEADER ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=220)
else:
    st.title("G-Code Checker")
st.markdown(f"<p style='color: #64748b; margin-top: -15px;'>{t('desc')}</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader(t("up"), type=["gcode", "gc", "txt"], label_visibility="collapsed")

if uploaded_file is None:
    st.markdown(f"""<div style="text-align: center; padding: 20px 0;"><h3 style="color: #334155;">📥 {t('empty_head')}</h3><p style="opacity: 0.7;">{t('empty_desc')}</p></div>""", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='feat-card'><h4>📊 Baskı Özeti</h4><p>Katman, Z-Hop, Retraction ve detaylı süre analizleri hesaplanır.</p></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='feat-card'><h4>🧩 Yapısal Kontrol</h4><p>Isıtma, Home ve Klipper makroları gibi rutinler denetlenir.</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='feat-card'><h4>🧭 XY Toolpath</h4><p>G-Code koordinatlarıyla tabla üzerinde 2D önizleme çizilir.</p></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='feat-card'><h4>⚠️ Risk Taraması</h4><p>Sınır ihlalleri, anormal hızlar ve Z sıçramaları tespit edilir.</p></div>", unsafe_allow_html=True)
else:
    with st.spinner(t("analyzing")):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gcode") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        checker = GCodeChecker(bed_x=bed_x, bed_y=bed_y, max_z=max_z, lang=LANG)
        issues = checker.check(tmp_path)
        structure = checker.analyze_structure(tmp_path)
        summary = checker.analyze_summary(tmp_path, filament_diameter=f_dia, filament_density=f_dens)
        toolpath_points = checker.get_toolpath_points(tmp_path)

    st.success(t("done"))
    tab1, tab2, tab3, tab4 = st.tabs(["📊 " + t("t_sum"), "🧭 " + t("t_prev"), "🧩 " + t("t_str"), "⚠️ " + t("t_err")])

    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        # Metrik Kartları
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t("time"), summary["total_time_text"])
        m2.metric(t("layer"), str(summary["layer_count"]))
        m3.metric(t("weight"), f"{summary['filament_weight_g']:.1f} g")
        m4.metric(t("len"), f"{summary['filament_used_m']:.2f} m")
        
        st.divider()
        col_left, col_right = st.columns(2)
        
        with col_left:
            # İŞTE BURASI: Detaylı İstatistik Tablosu (Z-Hop, Retraction, Süreler dahil)
            st.markdown(f"### {t('det_stats')}")
            detailed_data = [
                {"Metric": "Total Lines", "Value": f"{summary['total_lines']}"},
                {"Metric": "Print Time (Yazdırma)", "Value": checker.format_duration(summary["print_time_sec"])},
                {"Metric": "Travel Time (Boşta)", "Value": checker.format_duration(summary["travel_time_sec"])},
                {"Metric": "Average Print Speed", "Value": f"{summary['avg_print_speed']:.0f} mm/s"},
                {"Metric": "Average Travel Speed", "Value": f"{summary['avg_travel_speed']:.0f} mm/s"},
                {"Metric": "Max Feedrate", "Value": f"{summary['max_feedrate']:.0f} mm/min"},
                {"Metric": "Print Distance", "Value": f"{summary['print_dist_mm']:.1f} mm"},
                {"Metric": "Travel Distance", "Value": f"{summary['travel_dist_mm']:.1f} mm"},
                {"Metric": "Retraction Count", "Value": f"{summary['retract_count']}"},
                {"Metric": "Retraction Distance", "Value": f"{summary['retract_dist_mm']:.1f} mm"},
                {"Metric": "Z-Hop Count", "Value": f"{summary['zhop_count']}"},
                {"Metric": "Z-Hop Time", "Value": f"{summary['zhop_time_sec']:.2f} s"}
            ]
            st.dataframe(pd.DataFrame(detailed_data), use_container_width=True, hide_index=True)

        with col_right:
            # Eksen Bazlı İstatistikler
            st.markdown(f"### {t('axis_stats')}")
            axis_data = [
                {"Axis": "X Axis", "Mesafe": f"{summary['dist_x']:.1f} mm"},
                {"Axis": "Y Axis", "Mesafe": f"{summary['dist_y']:.1f} mm"},
                {"Axis": "Z Axis", "Mesafe": f"{summary['dist_z']:.1f} mm"},
                {"Axis": "Extruder (E)", "Mesafe": f"{summary['filament_used_m']*1000:.1f} mm"}
            ]
            st.dataframe(pd.DataFrame(axis_data), use_container_width=True, hide_index=True)
            
            st.markdown(f"<br>### {t('hist')}", unsafe_allow_html=True)
            if summary["speed_hist"]:
                df_h = pd.DataFrame(list(summary["speed_hist"].items()), columns=["Feedrate", "Time"]).set_index("Feedrate").sort_index()
                st.bar_chart(df_h, color="#38bdf8", height=200)

    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        if toolpath_points:
            fig, ax = plt.subplots(figsize=(8, 6), facecolor='#0f172a')
            ax.set_facecolor('#0f172a')
            ax.set_xlim(0, bed_x); ax.set_ylim(0, bed_y); ax.set_aspect("equal")
            ax.grid(True, linestyle="-", linewidth=0.5, color="#1e293b")
            ax.tick_params(colors="#64748b", labelsize=9)
            
            # Extrusion: Neon Mavi | Travel: Turuncu
            ext_pts = [[(p["x1"], p["y1"]), (p["x2"], p["y2"])] for p in toolpath_points if p["type"] == "extrusion"]
            ax.add_collection(LineCollection(ext_pts, linewidths=0.7, colors='#38bdf8', alpha=0.9))
            
            show_travel = st.toggle(t("show_trv"), value=False)
            if show_travel:
                trv_pts = [[(p["x1"], p["y1"]), (p["x2"], p["y2"])] for p in toolpath_points if p["type"] == "travel"]
                ax.add_collection(LineCollection(trv_pts, linewidths=0.3, colors='#f97316', alpha=0.5))
            
            st.pyplot(fig)
            plt.close(fig)

    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        res = []
        emoji_map = {"OK": "🟢 OK", "WARNING": "🟠 UYARI", "ERROR": "🔴 HATA", "INFO": "🔵 INFO"}
        for c in structure["start_checks"] + structure["end_checks"]:
            res.append({"Durum": emoji_map.get(c["status"], c["status"]), "Kontrol": c["name"], "Mesaj": c["message"]})
        st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

    with tab4:
        st.markdown("<br>", unsafe_allow_html=True)
        if not issues: st.success(t("no_err"))
        else:
            df_i = pd.DataFrame([{"Satır": i.line_no, "Tür": i.severity, "Mesaj": i.message, "Kod": i.line} for i in issues])
            st.dataframe(df_i, use_container_width=True, hide_index=True)
            csv = df_i.to_csv(index=False).encode("utf-8")
            st.download_button(t("dl_btn"), data=csv, file_name="gcode_rapor.csv", mime="text/csv")