
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os

# ==========================================
# إعدادات الصفحة
# ==========================================

st.set_page_config(
    page_title="التوأم الرقمي الذكي لمحصول الفلفل",
    page_icon="🌱",
    layout="wide"
)

# ==========================================
# تنسيق الواجهة العربية RTL
# ==========================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif;
    direction: rtl;
}

.main {
    direction: rtl;
}

h1, h2, h3, p, label {
    text-align: right;
}

div[data-testid="stMetric"] {
    direction: rtl;
    text-align: right;
    border: 1px solid #dddddd;
    padding: 12px;
    border-radius: 10px;
}

.stButton button {
    width: 100%;
    font-family: 'Cairo', sans-serif;
    font-weight: bold;
}

.notice {
    padding: 14px;
    border-radius: 10px;
    background-color: #fff3cd;
    color: #664d03;
    direction: rtl;
    text-align: right;
    margin-bottom: 15px;
}

.info-box {
    padding: 14px;
    border-radius: 10px;
    background-color: #e8f3ff;
    color: #084298;
    direction: rtl;
    text-align: right;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# عنوان البرنامج
# ==========================================

st.title("🌱 التوأم الرقمي الذكي لمحصول الفلفل")

st.markdown("""
نظام بحثي تفاعلي لمتابعة حالة النبات والتربة والمياه والبيئة،
وتقديم مؤشرات أولية لدعم قرارات الري والتسميد.
""")

st.markdown("""
<div class="notice">
<strong>تنبيه بحثي:</strong>
هذه النسخة نموذج أولي. الحسابات والحدود المستخدمة تحتاج إلى
معايرة وفق نوع التربة والصنف ومرحلة النمو والظروف التجريبية.
لا تستخدم النتائج للتحكم الفعلي في الصمامات أو المضخات.
</div>
""", unsafe_allow_html=True)


# ==========================================
# تهيئة سجل البيانات
# ==========================================

if "records" not in st.session_state:
    st.session_state.records = []


# ==========================================
# دوال مساعدة
# ==========================================

def safe_divide(a, b):
    if b == 0:
        return 0
    return a / b


def analyze_notes(notes):
    """
    تحليل مبدئي للكلمات المفتاحية فقط.
    لا يمثل تشخيصًا مرضيًا أو نموذج ذكاء اصطناعي.
    """

    text = notes.strip().lower()

    findings = []

    keywords = {
        "ذبول": "قد يرتبط بإجهاد مائي أو مشكلة في الجذور أو الملوحة.",
        "منكمش": "قد يشير إلى إجهاد مائي أو حراري أو مشكلة فسيولوجية.",
        "اصفرار": "قد يرتبط بنقص عناصر غذائية أو زيادة الري أو مشكلات الجذور.",
        "احتراق": "قد يرتبط بإجهاد ملحي أو حراري أو مشكلة تغذوية.",
        "بقع": "تحتاج إلى فحص بصري لتحديد طبيعة البقع وموقعها.",
        "عفن": "يحتاج إلى فحص الجذور أو الأنسجة المصابة.",
        "حشرات": "يُنصح بفحص السطحين العلوي والسفلي للأوراق.",
        "تساقط": "قد يرتبط بالإجهاد الحراري أو المائي أو ضعف التلقيح.",
        "تجعد": "قد يرتبط بإجهاد بيئي أو تغذوي أو إصابة حشرية."
    }

    for word, message in keywords.items():
        if word in text:
            findings.append((word, message))

    return findings


def calculate_depletion(fc, wp, moisture):
    """
    حساب نسبة استنزاف الماء المتاح بين السعة الحقلية
    ونقطة الذبول، باستخدام نفس أساس وحدات الرطوبة.
    """

    available_water = fc - wp

    if available_water <= 0:
        return None

    depletion = (fc - moisture) / available_water

    return float(np.clip(depletion, 0, 1))


def calculate_water_deficit(fc, moisture, root_depth):
    """
    تقدير عمق العجز المائي النظري بالملليمتر.
    الرطوبة والسعة الحقلية كنسبة حجمية %.
    عمق الجذور بالمتر.
    """

    difference = max(fc - moisture, 0) / 100

    deficit_mm = difference * root_depth * 1000

    return deficit_mm


# ==========================================
# الشريط الجانبي
# ==========================================

st.sidebar.header("⚙️ إعداد التجربة")

experiment_name = st.sidebar.text_input(
    "اسم التجربة",
    "تجربة الفلفل رقم 1"
)

crop_variety = st.sidebar.text_input(
    "صنف الفلفل",
    "فلفل"
)

plant_age = st.sidebar.number_input(
    "عمر النبات (يوم)",
    min_value=0,
    max_value=365,
    value=30
)

growth_stage = st.sidebar.selectbox(
    "مرحلة النمو",
    [
        "مرحلة النمو الخضري",
        "مرحلة التزهير",
        "مرحلة العقد",
        "مرحلة نمو الثمار",
        "مرحلة الحصاد"
    ]
)

observation_date = st.sidebar.date_input(
    "تاريخ القياس",
    datetime.today().date()
)

st.sidebar.divider()

st.sidebar.info(
    "وضع التشغيل الحالي: دعم القرار فقط. "
    "لا يوجد اتصال فعلي بالحساسات أو وحدات التحكم."
)


# ==========================================
# التبويبات
# ==========================================

tabs = st.tabs([
    "🏠 لوحة التحكم",
    "🌤️ البيئة",
    "🌱 التربة",
    "💧 المياه والتسميد",
    "🍃 النبات",
    "📝 ملاحظات الباحث",
    "📊 سجل البيانات"
])


# ==========================================
# 1- لوحة التحكم
# ==========================================

with tabs[0]:

    st.header("لوحة متابعة التوأم الرقمي")

    st.write(
        "تعرض هذه الصفحة ملخصًا لحالة التجربة بناءً على "
        "القياسات التي تدخلها في الصفحات التالية."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("عمر النبات", f"{plant_age} يوم")
    col2.metric("مرحلة النمو", growth_stage)
    col3.metric("صنف المحصول", crop_variety)

    st.divider()

    st.subheader("مكونات النظام")

    c1, c2, c3 = st.columns(3)

    c1.info("🌤️ مراقبة الظروف البيئية")
    c2.info("🌱 متابعة حالة التربة")
    c3.info("💧 متابعة مياه الري والتسميد")

    c4, c5, c6 = st.columns(3)

    c4.info("🍃 متابعة نمو النبات")
    c5.info("🤖 دعم قرارات الإدارة")
    c6.info("📊 تسجيل وتحليل البيانات")

    st.markdown("""
    <div class="info-box">
    <strong>فكرة التوأم الرقمي:</strong>
    يتم إنشاء تمثيل رقمي لحالة النبات والتربة والبيئة،
    ثم مقارنة القياسات الفعلية بالحالة المتوقعة،
    واستخدام النتائج لتحسين قرارات الإدارة الزراعية.
    </div>
    """, unsafe_allow_html=True)


# ==========================================
# 2- بيانات البيئة
# ==========================================

with tabs[1]:

    st.header("🌤️ بيانات البيئة المحيطة")

    col1, col2 = st.columns(2)

    with col1:

        air_temp = st.number_input(
            "درجة حرارة الهواء (°C)",
            min_value=-5.0,
            max_value=60.0,
            value=28.0
        )

        relative_humidity = st.number_input(
            "الرطوبة النسبية (%)",
            min_value=0.0,
            max_value=100.0,
            value=65.0
        )

        solar_radiation = st.number_input(
            "الإشعاع الشمسي (W/m²)",
            min_value=0.0,
            max_value=1500.0,
            value=500.0
        )

    with col2:

        wind_speed = st.number_input(
            "سرعة الهواء (m/s)",
            min_value=0.0,
            max_value=30.0,
            value=1.0
        )

        forecast_temp = st.number_input(
            "درجة الحرارة المتوقعة (°C)",
            min_value=-5.0,
            max_value=60.0,
            value=30.0
        )

        rain_forecast = st.number_input(
            "الأمطار المتوقعة (mm)",
            min_value=0.0,
            max_value=300.0,
            value=0.0
        )

    st.caption(
        "يمكن لاحقًا ربط هذه المدخلات بمحطة طقس أو خدمة توقعات جوية."
    )


# ==========================================
# 3- بيانات التربة
# ==========================================

with tabs[2]:

    st.header("🌱 بيانات التربة")

    col1, col2 = st.columns(2)

    with col1:

        soil_moisture = st.number_input(
            "الرطوبة الحجمية الحالية VWC (%)",
            min_value=0.0,
            max_value=100.0,
            value=25.0
        )

        field_capacity = st.number_input(
            "السعة الحقلية FC (%)",
            min_value=0.1,
            max_value=100.0,
            value=35.0
        )

        wilting_point = st.number_input(
            "نقطة الذبول WP (%)",
            min_value=0.0,
            max_value=99.0,
            value=15.0
        )

    with col2:

        root_depth = st.number_input(
            "عمق منطقة الجذور (m)",
            min_value=0.01,
            max_value=2.0,
            value=0.30
        )

        soil_ec = st.number_input(
            "التوصيل الكهربائي للتربة EC (dS/m)",
            min_value=0.0,
            max_value=30.0,
            value=1.5
        )

        soil_ph = st.number_input(
            "درجة حموضة التربة pH",
            min_value=0.0,
            max_value=14.0,
            value=6.5
        )

    if wilting_point >= field_capacity:
        st.error("يجب أن تكون السعة الحقلية أكبر من نقطة الذبول.")

    elif soil_moisture > 100:
        st.error("قيمة الرطوبة غير صحيحة.")

    else:
        st.success("تم إدخال بيانات التربة.")


# ==========================================
# 4- بيانات المياه والتسميد
# ==========================================

with tabs[3]:

    st.header("💧 بيانات مياه الري والمحلول المغذي")

    col1, col2 = st.columns(2)

    with col1:

        irrigation_ec = st.number_input(
            "ملوحة مياه الري EC (dS/m)",
            min_value=0.0,
            max_value=30.0,
            value=0.8
        )

        irrigation_ph = st.number_input(
            "pH مياه الري",
            min_value=0.0,
            max_value=14.0,
            value=6.5
        )

        flow_rate = st.number_input(
            "تصرف نظام الري (L/h)",
            min_value=0.0,
            max_value=100000.0,
            value=6.0
        )

    with col2:

        nitrogen = st.number_input(
            "تركيز النيتروجين N (mg/L)",
            min_value=0.0,
            max_value=5000.0,
            value=100.0
        )

        phosphorus = st.number_input(
            "تركيز الفوسفور P (mg/L)",
            min_value=0.0,
            max_value=5000.0,
            value=20.0
        )

        potassium = st.number_input(
            "تركيز البوتاسيوم K (mg/L)",
            min_value=0.0,
            max_value=5000.0,
            value=120.0
        )

    st.caption(
        "أدخل التركيز الفعلي المقاس أو المحسوب للمحلول. "
        "هذه القيم لا تمثل توصية تسميد عامة."
    )


# ==========================================
# 5- بيانات النبات
# ==========================================

with tabs[4]:

    st.header("🍃 القياسات الفسيولوجية والنمو الخضري")

    col1, col2 = st.columns(2)

    with col1:

        plant_height = st.number_input(
            "ارتفاع النبات (cm)",
            min_value=0.0,
            max_value=500.0,
            value=35.0
        )

        leaf_count = st.number_input(
            "عدد الأوراق",
            min_value=0,
            max_value=10000,
            value=18
        )

        lai = st.number_input(
            "دليل مساحة الأوراق LAI",
            min_value=0.0,
            max_value=20.0,
            value=1.5
        )

    with col2:

        stem_diameter = st.number_input(
            "قطر الساق (mm)",
            min_value=0.0,
            max_value=100.0,
            value=8.0
        )

        flower_count = st.number_input(
            "عدد الأزهار",
            min_value=0,
            max_value=10000,
            value=5
        )

        fruit_count = st.number_input(
            "عدد الثمار",
            min_value=0,
            max_value=10000,
            value=2
        )

    st.subheader("بيانات الإنتاج")

    harvested_fruits = st.number_input(
        "عدد الثمار المحصودة",
        min_value=0,
        max_value=100000,
        value=0
    )

    harvested_weight = st.number_input(
        "وزن المحصول المحصود (kg)",
        min_value=0.0,
        max_value=100000.0,
        value=0.0
    )


# ==========================================
# 6- ملاحظات الباحث
# ==========================================

with tabs[5]:

    st.header("📝 التفاعل مع الباحث")

    st.write(
        "اكتب وصفًا لما تلاحظه على النباتات. "
        "سيبحث البرنامج عن بعض الكلمات المفتاحية "
        "ويعرض احتمالات أولية للفحص."
    )

    researcher_notes = st.text_area(
        "اكتب ملاحظاتك هنا",
        placeholder=(
            "مثال: لاحظت اصفرار الأوراق السفلية "
            "وانكماش بعض الأوراق..."
        ),
        height=150
    )

    uploaded_image = st.file_uploader(
        "ارفع صورة للنبات (اختياري)",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_image is not None:
        st.image(
            uploaded_image,
            caption="الصورة المرفوعة",
            use_container_width=True
        )

        st.info(
            "الصورة محفوظة للعرض في هذه الجلسة فقط. "
            "لم يتم إجراء تحليل آلي للصورة في هذه النسخة."
        )

    if st.button("تحليل الملاحظات"):

        results = analyze_notes(researcher_notes)

        if len(results) == 0:
            st.info(
                "لم يتم العثور على كلمات مفتاحية معروفة. "
                "حاول وصف الأعراض بصورة أكثر تحديدًا."
            )

        else:
            st.subheader("نتائج الفحص الأولي")

            for word, message in results:
                st.warning(
                    f"الكلمة: {word}\n\nالاحتمال: {message}"
                )

            st.caption(
                "هذه النتائج ليست تشخيصًا مؤكدًا. "
                "يجب مراجعة صور النبات والقياسات والفحص الحقلي."
            )


# ==========================================
# 7- محرك دعم القرار
# ==========================================

st.divider()

st.header("🤖 محرك دعم قرارات الري")

st.write(
    "يستخدم المحرك بيانات الرطوبة والسعة الحقلية ونقطة الذبول "
    "لتقدير نسبة استنزاف الماء المتاح."
)

depletion_threshold = st.slider(
    "عتبة استنزاف الماء التي تستدعي المراجعة (%)",
    min_value=5,
    max_value=80,
    value=30
)

if wilting_point >= field_capacity:

    st.error(
        "لا يمكن حساب استنزاف الماء. "
        "راجع قيم السعة الحقلية ونقطة الذبول."
    )

else:

    depletion = calculate_depletion(
        field_capacity,
        wilting_point,
        soil_moisture
    )

    deficit_mm = calculate_water_deficit(
        field_capacity,
        soil_moisture,
        root_depth
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "استنزاف الماء المتاح",
        f"{depletion * 100:.1f}%"
    )

    col2.metric(
        "العجز النظري عن FC",
        f"{deficit_mm:.2f} mm"
    )

    col3.metric(
        "رطوبة التربة الحالية",
        f"{soil_moisture:.1f}%"
    )

    st.progress(float(depletion))

    if soil_moisture < wilting_point:

        st.error(
            "الرطوبة أقل من نقطة الذبول المدخلة. "
            "يجب التحقق من القياس وحالة النبات والتربة."
        )

    elif depletion * 100 >= depletion_threshold:

        st.warning(
            "اقتراح أولي: مراجعة الحاجة إلى الري. "
            "تحقق من حالة النبات وتوزيع الرطوبة وعمق الجذور "
            "قبل اعتماد القرار."
        )

    else:

        st.success(
            "لا تتجاوز نسبة الاستنزاف العتبة المحددة. "
            "استمر في المتابعة وفق برنامج القياس."
        )

    st.info(
        "العجز النظري بالملليمتر لا يساوي حجم المياه الواجب ضخه "
        "مباشرة؛ إذ يلزم معرفة المساحة المروية وكفاءة التطبيق "
        "وتوزيع الرطوبة والاحتياجات الفعلية للمحصول."
    )


# ==========================================
# 8- فحص الملوحة ودرجة الحموضة
# ==========================================

st.header("🧪 مؤشرات الملوحة ودرجة الحموضة")

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "EC مياه الري",
        f"{irrigation_ec:.2f} dS/m"
    )

    if irrigation_ec > 2:
        st.warning(
            "قيمة EC مرتفعة نسبيًا. "
            "راجع ملاءمتها للمحصول وظروف التربة."
        )
    else:
        st.success(
            "لا يوجد تنبيه وفق الحد الاسترشادي المستخدم هنا."
        )

with col2:

    st.metric(
        "pH مياه الري",
        f"{irrigation_ph:.2f}"
    )

    if irrigation_ph < 5.5 or irrigation_ph > 7.5:
        st.warning(
            "راجع قيمة pH ومدى ملاءمتها للمحلول المغذي."
        )
    else:
        st.success(
            "قيمة pH داخل النطاق الاسترشادي المعروض."
        )

st.caption(
    "حدود التنبيه هنا استرشادية وليست حدودًا ثابتة لجميع "
    "أصناف الفلفل أو نظم الزراعة."
)


# ==========================================
# 9- حفظ القياسات
# ==========================================

st.divider()

st.header("💾 حفظ بيانات التجربة")

if st.button("حفظ القياسات الحالية"):

    record = {
        "تاريخ القياس": str(observation_date),
        "اسم التجربة": experiment_name,
        "الصنف": crop_variety,
        "عمر النبات": plant_age,
        "مرحلة النمو": growth_stage,

        "حرارة الهواء": air_temp,
        "الرطوبة النسبية": relative_humidity,
        "الإشعاع الشمسي": solar_radiation,
        "سرعة الهواء": wind_speed,

        "رطوبة التربة": soil_moisture,
        "السعة الحقلية": field_capacity,
        "نقطة الذبول": wilting_point,
        "عمق الجذور": root_depth,
        "EC التربة": soil_ec,
        "pH التربة": soil_ph,

        "EC مياه الري": irrigation_ec,
        "pH مياه الري": irrigation_ph,
        "تصرف الري": flow_rate,

        "N": nitrogen,
        "P": phosphorus,
        "K": potassium,

        "ارتفاع النبات": plant_height,
        "عدد الأوراق": leaf_count,
        "LAI": lai,
        "قطر الساق": stem_diameter,
        "عدد الأزهار": flower_count,
        "عدد الثمار": fruit_count,

        "عدد الثمار المحصودة": harvested_fruits,
        "وزن المحصول kg": harvested_weight,

        "ملاحظات الباحث": researcher_notes
    }

    st.session_state.records.append(record)

    st.success("تم حفظ القياسات في سجل الجلسة الحالية.")


# ==========================================
# 10- سجل البيانات والتصدير
# ==========================================

with tabs[6]:

    st.header("📊 سجل القياسات")

    if len(st.session_state.records) > 0:

        df = pd.DataFrame(st.session_state.records)

        st.dataframe(
            df,
            use_container_width=True
        )

        csv_data = df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="⬇️ تحميل سجل البيانات CSV",
            data=csv_data,
            file_name="pepper_experiment_data.csv",
            mime="text/csv"
        )

        st.metric(
            "عدد سجلات القياس",
            len(df)
        )

        if st.button("مسح سجل الجلسة"):
            st.session_state.records = []
            st.rerun()

    else:

        st.info(
            "لا توجد بيانات محفوظة حتى الآن. "
            "أدخل القياسات واضغط على حفظ القياسات الحالية."
        )


# ==========================================
# 11- حدود النسخة الحالية وخطة التطوير
# ==========================================

st.divider()

with st.expander("🔬 ما الذي يحتاج إلى تطوير في النسخة القادمة؟"):

    st.markdown("""
    **1. التنبؤ بالنمو الخضري**
    - تدريب نماذج ML على ارتفاع النبات وLAI وعدد الأوراق.
    - توقع النمو خلال الأيام القادمة.
    - مقارنة القيم المتوقعة بالقياسات الفعلية.

    **2. التنبؤ بالإنتاجية**
    - جمع بيانات المحصول الفعلية.
    - تدريب نموذج لتوقع الإنتاجية وجودة الثمار.
    - اختبار النموذج على بيانات لم تدخل في التدريب.

    **3. التسميد الذكي**
    - تقدير احتياجات N وP وK وفق مرحلة النمو.
    - إدخال EC وpH للمحلول والتربة.
    - استخدام قياسات النبات والتحليل المعملي.

    **4. التوأم الرقمي الديناميكي**
    - بناء نموذج يصف انتقال الماء في منطقة الجذور.
    - تمثيل امتصاص النبات للماء والعناصر.
    - تحديث حالة التوأم باستخدام القياسات الحقيقية.

    **5. التحسين واتخاذ القرار**
    - تطوير خوارزمية Optimization.
    - تقليل استهلاك المياه والأسمدة.
    - الحفاظ على النمو والإنتاجية ضمن القيود الزراعية.

    **6. الاتصال بالأجهزة**
    - ربط Arduino أو ESP32.
    - استقبال قراءات الحساسات.
    - اختبار التحكم في بيئة آمنة قبل أي تشغيل ميداني.
    """)

st.caption(
    "Pepper Digital Twin | Research Prototype"
)
