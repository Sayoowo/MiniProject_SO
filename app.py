from json import tool

import pandas as pd
import streamlit as st
import altair as alt

"""
Student Performance dashboard.
Loads student data from a CSV, lets users filter it in the sidebar,
and shows KPIs, charts and insights about study habits, work hours and attendance.
"""

st.set_page_config(page_title="Student Performance", layout="wide")
st.title("Studnet Performance ")

DATA_PATH = "data/student_performance.csv"


@st.cache_data# read the CSV once and reuse it, instead of re-reading on every click
def load_data(path):
    df = pd.read_csv(path)
    df = df.dropna(how="all")  # drop rows that are empty
    text = df.select_dtypes(include="object").columns
    df[text] = df[text].fillna("No data")
    return df


df = load_data(DATA_PATH)

st.caption(
    "Blank values: fully empty rows are dropped, blank text fields show "
    "'No data', and blank numbers are left empty so they don't distort totals or averages."
)

st.sidebar.header("Filters")
course_options = sorted(df["course"].unique())
selected_courses = st.sidebar.multiselect(
    "Course",
    options=course_options,
    default=course_options,
)
min_attendance = st.sidebar.slider(
    "Minimum attendance (%)",
    min_value=0,
    max_value=100,
    value=0,
)
# Keep rows that match BOTH filters. Each condition needs brackets because & runs before >=
filtered = df[
filtered = df[
    df["course"].isin(selected_courses)
    & (df["attendance_pct"] >= min_attendance)
]
# Stop here if no rows are left, so the charts and averages below never run on empty data
if filtered.empty:
    st.warning(
        "No students match these filters, Try selecting more courses"
        "or lowering the minimum attendance."
    )
    st.stop


#Chart 1: Average final score by course
st.subheader("Average final score by course")
course_avg = (
    filtered.groupby("course")["final_score"]
    .mean()
    .reset_index()
    .sort_values("final_score", ascending=False)
)
bars = alt.Chart(course_avg).mark_bar().encode(
    x = alt.X("course:N", title="Course", axis=alt.Axis(labelAngle=0)),
    y = alt.Y(
    "final_score:Q",
    title="Average final score(points, 0-100)",
    scale=alt.Scale(domain=[0, 100]), # fix the axis at 0–100 so small gaps don't look exaggerated
),
    tooltip = [
    alt.Tooltip("course:N", title="Course"),
    alt.Tooltip("final_score:Q", title="Average final score"),
    ],
)
labels = bars.mark_text(dy=-10, fontSize=14).encode(text="final_score:Q")

chart1 = (bars + labels).properties(height=350).configure_axis(
    labelFontSize=14,
    titleFontSize=15,
)

st.altair_chart(chart1, use_container_width=True)

st.caption(
    "Bar chart of the average final score (out of 100) in each course for the "
    "selected students. The exact value is shown above each bar; hover over a bar for details."
)
#chart 2: Study hours vs final score
st.subheader("Study hours vs final score")
scatter_data = filtered.dropna(subset=["study_hours_week", "final_score"]) # A dot needs both x and y, so drop students missing either (for this chart only)
scatter = alt.Chart(scatter_data).mark_circle(size=80, opacity=0.7).encode(
    x=alt.X("study_hours_week:Q", title="Study hours per week"),
    y=alt.Y(
        "final_score:Q",
        title="Final score (points, 0-100)",
        scale=alt.Scale(domain=[0, 100]),
    ),
    tooltip=[
        alt.Tooltip("course:N", title="Course"),
        alt.Tooltip("study_hours_week:Q", title="Study hrs/week"),
        alt.Tooltip("final_score:Q", title="Final score"),
        alt.Tooltip("letter_grade:N", title="Grade"),
    ],
)
chart2 = scatter.properties(height=380).interactive().configure_axis(
    labelFontSize=14,
    titleFontSize=15,
)

st.altair_chart(chart2, use_container_width=True)

st.caption(
    "Scatter plot where each dot is one student: weekly study hours across the bottom, "
    "final score up the side. Students with no recorded study hours are left out of this chart. "
    "Hover over a dot for details; scroll to zoom, drag to move, double-click to reset."
)
# chart 3: Letter grade distribution
st.subheader("Number of students by letter grade")
grade_counts = filtered["letter_grade"].value_counts().reset_index()
grade_counts.columns = ["letter_grade", "students"]
grade_order = ["A", "B", "C", "D", "F", "No data"] # Grades have a natural order, so force A → F instead of alphabetical/size order

grade_bars = alt.Chart(grade_counts).mark_bar().encode(
    x=alt.X(
        "Letter_grade:N",
        title="Letter grade",
        sort=grade_order,
        axis=alt.Axis(labelAngle=0),
    ),
    y = alt.Y("students:Q", title="Number of students"),
    tooltip = [
    alt.Tooltip("letter_grade:N", title="Grade"),
    alt.Tooltip("students:Q", title="Students"),
    ],
)
grade_labels = grade_bars.mark_text(dy=-10, fontSize=14).encode(text="students:Q")

chart3 = (grade_bars + grade_labels).properties(height=350).configure_axis(
    labelFontSize=14,
    titleFontSize=15,
)

st.altair_chart(chart3, use_container_width=True)

st.caption(
    "Bar chart counting how many of the selected students received each letter grade, "
    "in order from A to F. The count is shown above each bar."
)

# ---------- Insights ----------
st.subheader("Key insights")

PASS_GRADES = ["A", "B", "C"]
filtered = filtered.assign(passed=filtered["letter_grade"].isin(PASS_GRADES))

# --- Q1: Can work hours affect study habits? ---
work_summary = filtered.groupby("work_hours_week").agg(
    avg_study=("study_hours_week", "mean"),
    pass_rate=("passed", "mean"),
    students=("passed", "size"),
)

if len(work_summary) >= 2:
    least = work_summary.index.min()
    most = work_summary.index.max()
    q1 = (
        f"**1. Work hours and study habits:** Students working {least} hours per week study "
        f"**{work_summary.loc[least, 'avg_study']:.1f} hours** per week on average and "
        f"**{work_summary.loc[least, 'pass_rate'] * 100:.0f}%** pass. Students working {most} hours "
        f"study **{work_summary.loc[most, 'avg_study']:.1f} hours** and "
        f"**{work_summary.loc[most, 'pass_rate'] * 100:.0f}%** pass."
    )
else:
    q1 = "**1. Work hours and study habits:** The current filters include only one work-hours level, so there is nothing to compare."

# --- Q2: How important is it to attend class? ---
high_att = filtered[filtered["attendance_pct"] >= 80]
low_att = filtered[filtered["attendance_pct"] < 80]

if not high_att.empty and not low_att.empty:
    q2 = (
        f"**2. Attendance:** Students with 80% attendance or higher average "
        f"**{high_att['final_score'].mean():.1f} points** and **{high_att['passed'].mean() * 100:.0f}%** pass. "
        f"Students below 80% average **{low_att['final_score'].mean():.1f} points** and "
        f"**{low_att['passed'].mean() * 100:.0f}%** pass."
    )
else:
    q2 = "**2. Attendance:** All selected students are on the same side of 80% attendance, so there is nothing to compare."

# --- Q3: Which major works with a job on the side? ---
group_col = "major" if "major" in filtered.columns else "course"
workers = filtered[filtered["work_hours_week"] > 0]

if not workers.empty:
    by_group = workers.groupby(group_col).agg(
        pass_rate=("passed", "mean"),
        avg_work=("work_hours_week", "mean"),
        students=("passed", "size"),
    ).sort_values("pass_rate", ascending=False)

    best = by_group.index[0]
    worst = by_group.index[-1]
    q3 = (
        f"**3. Studying with a job:** Among the {len(workers)} students who work, **{best}** has the "
        f"highest pass rate at **{by_group.loc[best, 'pass_rate'] * 100:.0f}%** "
        f"(averaging {by_group.loc[best, 'avg_work']:.1f} work hours per week). "
        f"**{worst}** has the lowest at **{by_group.loc[worst, 'pass_rate'] * 100:.0f}%**."
    )
else:
    q3 = "**3. Studying with a job:** None of the selected students work, so there is nothing to compare."

st.markdown(q1)
st.markdown(q2)
st.markdown(q3)

st.caption(
    "Insights are recalculated from the students selected in the sidebar. "
    "'Passing' means a letter grade of C or better. 'Working' means more than 0 work hours per week."
)
# --- Q4: Do first-gen students work harder? ---
FIRST_GEN_COL = "first_gen"   # ← change if your column has a different name

if FIRST_GEN_COL in filtered.columns:
    fg = filtered.groupby(FIRST_GEN_COL).agg(
        avg_study=("study_hours_week", "mean"),
        avg_work=("work_hours_week", "mean"),
        avg_score=("final_score", "mean"),
        students=("final_score", "size"),
    )

    if len(fg) >= 2:
        lines = []
        for group, row in fg.iterrows():
            lines.append(
                f"first-gen = **{group}** ({row['students']} students) study "
                f"**{row['avg_study']:.1f} hrs/week**, work **{row['avg_work']:.1f} hrs/week**, "
                f"and average **{row['avg_score']:.1f} points**"
            )
        q4 = "**4. First-generation students:** Students with " + "; students with ".join(lines) + "."
    else:
        q4 = "**4. First-generation students:** The current filters include only one group, so there is nothing to compare."
else:
    q4 = f"**4. First-generation students:** No '{FIRST_GEN_COL}' column was found in the data."




st.subheader("Preview")
col1, col2, col3 = st.columns(3)
avg_score = filtered["final_score"].mean()
overall_avg = df["final_score"].mean()
col1.metric("Students", len(filtered))
col2.metric(
    "Average final score",
    f"{avg_score:.1f} pts",
    delta=f"{avg_score - overall_avg:+.1f} pts vs all students",
)
col3.metric(
    "Average attendance",
    f"{filtered['attendance_pct'].mean():.1f}%",
)