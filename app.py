
import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import datetime, date
from database import get_connection, initialize_database

st.set_page_config(
    page_title="Pepper Digital Twin",
    page_icon="🌱",
    layout="wide"
)

initialize_database()

def query(sql, params=()):
    conn = get_connection()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def execute(sql, params=()):
    conn = get_connection()
    conn.execute(sql, params)
    conn.commit()
    conn.close()

st.markdown("""
<style>
.main {
    direction: rtl;
}
.block-container {
    padding-top: 2rem;
}
</style>
""", unsafe_allow_html=True)

st.title("🌱 Pepper Digital Twin")
st.caption("Smart Irrigation and Fertigation Management System")

menu = [
    "لوحة التحكم",
    "إدارة التجارب",
    "إدارة المعاملات",
    "إدارة القطع والنباتات",
    "تسجيل قياسات التربة والجو",
    "تسجيل نمو النبات",
    "إدارة الري",
    "إدارة التسميد",
    "تسجيل الحصاد",
    "بيانات الحساسات",
    "الذكاء الاصطناعي",
    "قاعدة البيانات"
]

page = st.sidebar.radio("القائمة الرئيسية", menu)

# --------------------------------------------------
# Dashboard
# --------------------------------------------------

if page == "لوحة التحكم":

    st.header("لوحة متابعة النظام")

    experiments = query("SELECT * FROM experiments")
    plots = query("SELECT * FROM plots")
    plants = query("SELECT * FROM plants")
    observations = query("SELECT * FROM plot_observations")
    harvests = query("SELECT * FROM harvests")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("التجارب", len(experiments))
    c2.metric("القطع التجريبية", len(plots))
    c3.metric("النباتات", len(plants))
    c4.metric("سجلات الحصاد", len(harvests))

    st.subheader("آخر قياسات التربة والجو")

    if not observations.empty:
        st.dataframe(
            observations.tail(10),
            use_container_width=True
        )
    else:
        st.info("لم يتم تسجيل قياسات حتى الآن.")

    if not harvests.empty:
        st.subheader("الإنتاجية المسجلة")
        st.dataframe(harvests, use_container_width=True)

# --------------------------------------------------
# Experiments
# --------------------------------------------------

elif page == "إدارة التجارب":

    st.header("إضافة تجربة جديدة")

    with st.form("experiment_form"):

        name = st.text_input("اسم التجربة")
        crop = st.text_input("المحصول", "Pepper")
        location = st.text_input("موقع التجربة")
        start_date = st.date_input("تاريخ البداية")
        notes = st.text_area("ملاحظات")

        submit = st.form_submit_button("حفظ التجربة")

        if submit:
            if name.strip():
                execute("""
                INSERT INTO experiments
                (name, crop, location, start_date, notes)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    name, crop, location,
                    str(start_date), notes
                ))
                st.success("تم حفظ التجربة.")
                st.rerun()
            else:
                st.error("أدخل اسم التجربة.")

    st.subheader("التجارب المسجلة")
    st.dataframe(query("SELECT * FROM experiments"),
                 use_container_width=True)

# --------------------------------------------------
# Treatments
# --------------------------------------------------

elif page == "إدارة المعاملات":

    st.header("إضافة معاملة")

    experiments = query("SELECT * FROM experiments")

    if experiments.empty:
        st.warning("سجل تجربة أولًا.")
    else:
        exp_map = dict(zip(
            experiments["name"],
            experiments["id"]
        ))

        with st.form("treatment_form"):

            selected = st.selectbox(
                "التجربة",
                list(exp_map.keys())
            )

            name = st.text_input("اسم المعاملة")
            description = st.text_area("وصف المعاملة")

            submit = st.form_submit_button("حفظ")

            if submit:
                if name.strip():
                    execute("""
                    INSERT INTO treatments
                    (experiment_id, name, description)
                    VALUES (?, ?, ?)
                    """, (
                        exp_map[selected], name, description
                    ))
                    st.success("تم حفظ المعاملة.")
                    st.rerun()
                else:
                    st.error("أدخل اسم المعاملة.")

    st.dataframe(query("""
        SELECT t.id, e.name AS experiment,
               t.name AS treatment, t.description
        FROM treatments t
        JOIN experiments e ON e.id=t.experiment_id
    """), use_container_width=True)

# --------------------------------------------------
# Plots and plants
# --------------------------------------------------

elif page == "إدارة القطع والنباتات":

    st.header("تسجيل قطعة تجريبية")

    experiments = query("SELECT * FROM experiments")

    if experiments.empty:
        st.warning("سجل تجربة أولًا.")
    else:
        exp_map = dict(zip(experiments["name"], experiments["id"]))

        with st.form("plot_form"):

            exp_name = st.selectbox(
                "التجربة", list(exp_map.keys())
            )

            treatments = query("""
                SELECT * FROM treatments
                WHERE experiment_id=?
            """, (exp_map[exp_name],))

            if treatments.empty:
                st.warning("أضف معاملة لهذه التجربة أولًا.")
                submitted = False
            else:
                treatment_map = dict(zip(
                    treatments["name"], treatments["id"]
                ))

                treatment_name = st.selectbox(
                    "المعاملة", list(treatment_map.keys())
                )

                code = st.text_input("كود القطعة")
                replication = st.number_input(
                    "رقم المكرر", min_value=1, step=1
                )
                area = st.number_input(
                    "المساحة بالمتر المربع",
                    min_value=0.1, value=10.0
                )

                submitted = st.form_submit_button("حفظ القطعة")

                if submitted:
                    if code.strip():
                        try:
                            execute("""
                            INSERT INTO plots
                            (experiment_id, treatment_id,
                             plot_code, replication, area_m2)
                            VALUES (?, ?, ?, ?, ?)
                            """, (
                                exp_map[exp_name],
                                treatment_map[treatment_name],
                                code, replication, area
                            ))
                            st.success("تم حفظ القطعة.")
                            st.rerun()
                        except Exception as error:
                            st.error(str(error))
                    else:
                        st.error("أدخل كود القطعة.")

    st.divider()
    st.subheader("إضافة نبات لقطعة")

    plots = query("SELECT * FROM plots")

    if not plots.empty:

        plot_map = dict(zip(
            plots["plot_code"], plots["id"]
        ))

        with st.form("plant_form"):

            selected_plot = st.selectbox(
                "القطعة", list(plot_map.keys())
            )

            plant_code = st.text_input("كود النبات")

            submit = st.form_submit_button("إضافة النبات")

            if submit:
                if plant_code.strip():
                    try:
                        execute("""
                        INSERT INTO plants (plot_id, plant_code)
                        VALUES (?, ?)
                        """, (plot_map[selected_plot], plant_code))

                        st.success("تم تسجيل النبات.")
                        st.rerun()
                    except Exception as error:
                        st.error(str(error))
                else:
                    st.error("أدخل كود النبات.")

    st.subheader("القطع")
    st.dataframe(query("SELECT * FROM plots"),
                 use_container_width=True)

    st.subheader("النباتات")
    st.dataframe(query("""
        SELECT plants.*, plots.plot_code
        FROM plants
        JOIN plots ON plants.plot_id=plots.id
    """), use_container_width=True)

# --------------------------------------------------
# Soil and weather observations
# --------------------------------------------------

elif page == "تسجيل قياسات التربة والجو":

    st.header("إدخال قياسات التربة والجو")

    plots = query("SELECT * FROM plots")

    if plots.empty:
        st.warning("سجل قطعة تجريبية أولًا.")
    else:
        plot_map = dict(zip(plots["plot_code"], plots["id"]))

        with st.form("observation_form"):

            plot = st.selectbox("القطعة", list(plot_map.keys()))
            obs_date = st.date_input("التاريخ", date.today())

            moisture = st.number_input(
                "رطوبة التربة (%)", min_value=0.0, max_value=100.0
            )

            soil_ec = st.number_input(
                "EC التربة (dS/m)", min_value=0.0
            )

            soil_ph = st.number_input(
                "pH التربة", min_value=0.0, max_value=14.0
            )

            water_ec = st.number_input(
                "EC مياه الري (dS/m)", min_value=0.0
            )

            water_ph = st.number_input(
                "pH مياه الري", min_value=0.0, max_value=14.0
            )

            temperature = st.number_input(
                "درجة حرارة الهواء (°C)"
            )

            humidity = st.number_input(
                "الرطوبة النسبية (%)",
                min_value=0.0, max_value=100.0
            )

            notes = st.text_area("ملاحظات")

            submit = st.form_submit_button("حفظ القياسات")

            if submit:
                execute("""
                INSERT INTO plot_observations
                (plot_id, observation_date, soil_moisture,
                 soil_ec, soil_ph, water_ec, water_ph,
                 air_temperature, relative_humidity, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plot_map[plot], str(obs_date), moisture,
                    soil_ec, soil_ph, water_ec, water_ph,
                    temperature, humidity, notes
                ))

                st.success("تم حفظ القياسات.")
                st.rerun()

    data = query("""
        SELECT o.*, p.plot_code
        FROM plot_observations o
        JOIN plots p ON p.id=o.plot_id
        ORDER BY o.observation_date DESC
    """)

    st.dataframe(data, use_container_width=True)

    if not data.empty:
        st.subheader("تغير رطوبة التربة")
        fig = px.line(
            data.sort_values("observation_date"),
            x="observation_date",
            y="soil_moisture",
            color="plot_code",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Plant growth
# --------------------------------------------------

elif page == "تسجيل نمو النبات":

    st.header("تسجيل قياسات النمو الخضري")

    plants = query("""
        SELECT plants.id, plants.plant_code, plots.plot_code
        FROM plants
        JOIN plots ON plots.id=plants.plot_id
    """)

    if plants.empty:
        st.warning("سجل النباتات أولًا.")
    else:
        plant_map = {
            f"{r['plot_code']} - {r['plant_code']}": r["id"]
            for _, r in plants.iterrows()
        }

        with st.form("growth_form"):

            selected = st.selectbox(
                "النبات", list(plant_map.keys())
            )

            obs_date = st.date_input("تاريخ القياس")
            height = st.number_input(
                "ارتفاع النبات (cm)", min_value=0.0
            )
            width = st.number_input(
                "عرض المجموع الخضري (cm)", min_value=0.0
            )
            leaves = st.number_input(
                "عدد الأوراق", min_value=0, step=1
            )
            leaf_area = st.number_input(
                "مساحة الأوراق (cm²)", min_value=0.0
            )
            stage = st.text_input("مرحلة النمو")
            notes = st.text_area("ملاحظات بصرية")

            submit = st.form_submit_button("حفظ")

            if submit:
                execute("""
                INSERT INTO plant_observations
                (plant_id, observation_date,
                 plant_height_cm, canopy_width_cm,
                 leaf_number, leaf_area_cm2,
                 growth_stage, visual_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plant_map[selected], str(obs_date),
                    height, width, leaves, leaf_area,
                    stage, notes
                ))

                st.success("تم حفظ قياسات النبات.")
                st.rerun()

    st.dataframe(query("""
        SELECT po.*, p.plant_code
        FROM plant_observations po
        JOIN plants p ON p.id=po.plant_id
    """), use_container_width=True)

# --------------------------------------------------
# Irrigation
# --------------------------------------------------

elif page == "إدارة الري":

    st.header("تسجيل عمليات الري")

    plots = query("SELECT * FROM plots")

    if not plots.empty:

        plot_map = dict(zip(plots["plot_code"], plots["id"]))

        with st.form("irrigation_form"):

            plot = st.selectbox("القطعة", list(plot_map.keys()))
            start = st.text_input(
                "وقت البداية", datetime.now().isoformat(timespec="minutes")
            )
            end = st.text_input("وقت النهاية")
            volume = st.number_input(
                "كمية المياه (Liter)", min_value=0.0
            )
            method = st.selectbox(
                "طريقة الري", ["Drip", "Surface drip", "Subsurface drip"]
            )
            notes = st.text_area("ملاحظات")

            submit = st.form_submit_button("حفظ عملية الري")

            if submit:
                execute("""
                INSERT INTO irrigation_events
                (plot_id, start_time, end_time,
                 water_volume_liter, irrigation_method, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    plot_map[plot], start, end,
                    volume, method, notes
                ))

                st.success("تم تسجيل عملية الري.")
                st.rerun()

    st.dataframe(query("""
        SELECT i.*, p.plot_code
        FROM irrigation_events i
        JOIN plots p ON p.id=i.plot_id
    """), use_container_width=True)

# --------------------------------------------------
# Fertigation
# --------------------------------------------------

elif page == "إدارة التسميد":

    st.header("تسجيل عمليات التسميد")

    plots = query("SELECT * FROM plots")

    if not plots.empty:

        plot_map = dict(zip(plots["plot_code"], plots["id"]))

        with st.form("fertigation_form"):

            plot = st.selectbox("القطعة", list(plot_map.keys()))
            event_date = st.date_input("التاريخ")
            fertilizer = st.text_input("اسم السماد")
            nitrogen = st.number_input("N (g)", min_value=0.0)
            phosphorus = st.number_input("P (g)", min_value=0.0)
            potassium = st.number_input("K (g)", min_value=0.0)
            total = st.number_input("إجمالي كمية السماد (g)", min_value=0.0)
            notes = st.text_area("ملاحظات")

            submit = st.form_submit_button("حفظ التسميد")

            if submit:
                execute("""
                INSERT INTO fertigation_events
                (plot_id, event_date, fertilizer_name,
                 nitrogen_g, phosphorus_g, potassium_g,
                 total_amount_g, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plot_map[plot], str(event_date),
                    fertilizer, nitrogen, phosphorus,
                    potassium, total, notes
                ))

                st.success("تم حفظ عملية التسميد.")
                st.rerun()

    st.dataframe(query("""
        SELECT f.*, p.plot_code
        FROM fertigation_events f
        JOIN plots p ON p.id=f.plot_id
    """), use_container_width=True)

# --------------------------------------------------
# Harvest
# --------------------------------------------------

elif page == "تسجيل الحصاد":

    st.header("تسجيل الإنتاجية")

    plots = query("SELECT * FROM plots")

    if not plots.empty:

        plot_map = dict(zip(plots["plot_code"], plots["id"]))

        with st.form("harvest_form"):

            plot = st.selectbox("القطعة", list(plot_map.keys()))
            harvest_date = st.date_input("تاريخ الحصاد")
            fruits = st.number_input(
                "عدد الثمار", min_value=0, step=1
            )
            yield_kg = st.number_input(
                "وزن المحصول (kg)", min_value=0.0
            )
            average = st.number_input(
                "متوسط وزن الثمرة (g)", min_value=0.0
            )
            notes = st.text_area("ملاحظات")

            submit = st.form_submit_button("حفظ الحصاد")

            if submit:
                execute("""
                INSERT INTO harvests
                (plot_id, harvest_date, fruit_number,
                 yield_kg, average_fruit_weight_g, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    plot_map[plot], str(harvest_date),
                    fruits, yield_kg, average, notes
                ))

                st.success("تم تسجيل الحصاد.")
                st.rerun()

    st.dataframe(query("""
        SELECT h.*, p.plot_code
        FROM harvests h
        JOIN plots p ON p.id=h.plot_id
    """), use_container_width=True)

# --------------------------------------------------
# Sensors
# --------------------------------------------------

elif page == "بيانات الحساسات":

    st.header("إدارة الحساسات")

    plots = query("SELECT * FROM plots")

    if not plots.empty:

        plot_map = dict(zip(plots["plot_code"], plots["id"]))

        with st.form("sensor_form"):

            device = st.text_input("كود الجهاز")
            sensor_type = st.selectbox(
                "نوع الحساس",
                [
                    "Soil Moisture",
                    "Soil EC",
                    "Soil pH",
                    "Water EC",
                    "Water pH",
                    "Temperature",
                    "Humidity",
                    "Flow Meter",
                    "Load Cell"
                ]
            )
            plot = st.selectbox("القطعة", list(plot_map.keys()))
            unit = st.text_input("وحدة القياس")

            submit = st.form_submit_button("تسجيل الحساس")

            if submit:
                if device.strip():
                    execute("""
                    INSERT INTO sensors
                    (device_code, sensor_type, plot_id, unit)
                    VALUES (?, ?, ?, ?)
                    """, (
                        device, sensor_type, plot_map[plot], unit
                    ))
                    st.success("تم تسجيل الحساس.")
                    st.rerun()

    st.subheader("الحساسات المسجلة")
    st.dataframe(query("SELECT * FROM sensors"),
                 use_container_width=True)

    st.info(
        "استقبال القراءات الفعلية من Arduino وESP8266 "
        "سيتم تفعيله بعد بناء واجهة الاتصال."
    )

# --------------------------------------------------
# AI decisions
# --------------------------------------------------

elif page == "الذكاء الاصطناعي":

    st.header("محرك الذكاء الاصطناعي")

    st.warning(
        "لا يوجد نموذج مدرب في هذه النسخة. "
        "لن نعرض تنبؤات أو توصيات زراعية باعتبارها نتائج علمية."
    )

    st.subheader("تسجيل قرار بحثي مقترح")

    plots = query("SELECT * FROM plots")

    if not plots.empty:

        plot_map = dict(zip(plots["plot_code"], plots["id"]))

        with st.form("decision_form"):

            plot = st.selectbox("القطعة", list(plot_map.keys()))

            decision_type = st.selectbox(
                "نوع القرار",
                ["Irrigation", "Fertigation", "Combined"]
            )

            water = st.number_input(
                "المياه المقترحة (Liter)", min_value=0.0
            )
            n = st.number_input("N (g)", min_value=0.0)
            p = st.number_input("P (g)", min_value=0.0)
            k = st.number_input("K (g)", min_value=0.0)

            explanation = st.text_area("سبب القرار")
            model = st.text_input("اسم النموذج", "Manual research entry")

            submit = st.form_submit_button("تسجيل القرار")

            if submit:
                execute("""
                INSERT INTO ai_decisions
                (plot_id, decision_time, decision_type,
                 recommended_water_liter,
                 recommended_nitrogen_g,
                 recommended_phosphorus_g,
                 recommended_potassium_g,
                 model_name, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plot_map[plot],
                    datetime.now().isoformat(timespec="seconds"),
                    decision_type, water, n, p, k,
                    model, explanation
                ))

                st.success("تم تسجيل القرار كاقتراح غير منفذ.")
                st.rerun()

    st.subheader("سجل القرارات")

    st.dataframe(query("""
        SELECT d.*, p.plot_code
        FROM ai_decisions d
        LEFT JOIN plots p ON p.id=d.plot_id
        ORDER BY d.decision_time DESC
    """), use_container_width=True)

# --------------------------------------------------
# Database
# --------------------------------------------------

elif page == "قاعدة البيانات":

    st.header("عرض جداول قاعدة البيانات")

    tables = [
        "experiments",
        "treatments",
        "plots",
        "plants",
        "plot_observations",
        "plant_observations",
        "irrigation_events",
        "fertigation_events",
        "harvests",
        "sensors",
        "sensor_readings",
        "ai_decisions",
        "control_executions"
    ]

    selected_table = st.selectbox("اختر الجدول", tables)

    df = query(f"SELECT * FROM {selected_table}")

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "تحميل البيانات CSV",
        csv,
        file_name=f"{selected_table}.csv",
        mime="text/csv"
    )
