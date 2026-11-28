"""
Lecture 09 exercise
World Happiness dashboard with a diverging map of each country against the average

Purpose
Helps a policy analyst see which countries lead on happiness
and where scores fall below average.

@author: Ivan Logutov
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# Orange = below average, blue = above (safe for colour vision deficiency).
# Blue and orange mean above/below everywhere on the dashboard, so the bar highlight is dark grey.
BELOW, MIDPOINT, ABOVE = '#B35900', '#F5F5F5', '#1B5E9E'
HIGHLIGHT, CONTEXT = '#333333', '#BBBBBB'
NO_DATA = '#D9D9D9'   # land without data, a darker grey than the near-white midpoint

# Page configuration, title, purpose and data source
st.set_page_config(page_title="World Happiness Report", page_icon="🌐", layout='wide')
st.title("🌍 World Happiness Dashboard")
st.caption("Helps a policy analyst see which countries lead on happiness "
           "and where scores fall below average")
st.caption("Source: World Happiness Report 2023 | Kaggle")

# Data Ingestion
DATA = Path(__file__).parent.parent / "data" / "world_happiness_2023.csv"


@st.cache_data   # load and prepare once, not on every filter change
def load_data(path):
    df = pd.read_csv(path)
    df.columns = ['Country','Region','Score','GDP','Social_Support',
                  'Life_Expectancy','Freedom','Generosity','Corruption']

    # ISO-3 codes for the map: gapminder covers most country names, five need their code added
    iso = px.data.gapminder()[['country', 'iso_alpha']].drop_duplicates()
    df = df.merge(iso, left_on='Country', right_on='country', how='left').drop(columns='country')
    extra_iso = {'Czechia': 'CZE', 'Estonia': 'EST', 'Lithuania': 'LTU',
                 'Luxembourg': 'LUX', 'South Korea': 'KOR'}
    df['iso_alpha'] = df['iso_alpha'].fillna(df['Country'].map(extra_iso))
    assert df['iso_alpha'].notna().all(), "every country needs an ISO-3 code for the map"
    return df


df = load_data(DATA)

# The midpoint is the average of the countries in this dataset (63 of the report's ~137),
# so every label calls it the "63-country average" rather than a world figure
avg_all = df['Score'].mean()
AVG_LABEL = f"{len(df)}-country average"
df['Score_vs_avg'] = df['Score'] - avg_all
max_gap = df['Score_vs_avg'].abs().max()   # one symmetric colour range for every filter

# Side bar filters
with st.sidebar:
    st.header("Filters")
    regions = ['All Regions'] + sorted(df['Region'].unique().tolist())
    selected_region = st.selectbox("Region", regions)
    top_n = st.slider("Show top N", 5, 25, 15)


# filter data by region and top_n; keep='all' keeps countries tied at the cutoff
all_regions = selected_region == 'All Regions'
filtered = df if all_regions else df[df['Region'] == selected_region]
top = filtered.nlargest(top_n, 'Score', keep='all').sort_values('Score')

# KPI row
col1, col2, col3 = st.columns(3)
col1.metric("Countries", len(filtered))
# delta in the dashboard's blue/orange instead of the default green/red; no delta for all regions (always 0)
avg_gap = filtered['Score'].mean() - avg_all
col2.metric("Avg Score", f"{filtered['Score'].mean():.2f}",
            None if all_regions else f"{avg_gap:+.2f} vs {AVG_LABEL}",
            delta_color='blue' if avg_gap >= 0 else 'orange')
col3.metric("Happiest", filtered.nlargest(1,'Score')['Country'].values[0])

st.divider()


# ── Chart 1: top N countries, the leader highlighted ──────────────────────────
leader = top.iloc[-1]
top['Highlight'] = 'Other'
top.loc[top['Country'] == leader['Country'], 'Highlight'] = 'Leader'
scope = f"all {len(filtered)} countries" if all_regions else selected_region

fig = px.bar(top, x='Score', y='Country', orientation='h',
             color='Highlight',
             color_discrete_map={'Leader': HIGHLIGHT, 'Other': CONTEXT},
             category_orders={'Country': top['Country'].tolist()},
             hover_name='Country',
             hover_data={'Highlight': False, 'Country': False, 'Score': ':.2f'},
             labels={'Score': 'Happiness Score (0–10)', 'Country': ''},
             template='plotly_white',
             height=600)

fig.update_layout(title=dict(text=f"{leader['Country']} leads {scope} with a score of {leader['Score']:.2f}",
                             subtitle=dict(text=f"{'All' if len(top) == len(filtered) else 'Top'} "
                                                f"{len(top)} countries by happiness score, 2023")),
                  title_font=dict(family='Arial', size=13, color='slategrey'),
                  font=dict(family='Arial', size=12),
                  showlegend=False,
                  xaxis=dict(range=[0, 8.0], gridcolor='#EEEEEE'),
                  margin=dict(t=80, r=30))   # room for the last tick label, 8

# direct label on the leader only
fig.update_traces(texttemplate='%{x:.2f}', textposition='inside', insidetextanchor='end',
                  textfont=dict(color='white'), selector=dict(name='Leader'))


# ── Chart 2: diverging map, each country against the 63-country average ──────
# short titles with the region in the subtitle, so long region names still fit
if all_regions:
    region_gap = df.groupby('Region')['Score_vs_avg'].mean()
    map_title = f"{region_gap.idxmin()} falls furthest below the {AVG_LABEL} of {avg_all:.2f}"
    map_subtitle = f"All {len(df)} countries, happiness score minus their average, 2023"
else:
    n, n_above = len(filtered), int((filtered['Score_vs_avg'] > 0).sum())
    if n_above == 0:
        map_title = f"No country scores above the {AVG_LABEL}"
    elif n_above == n:
        map_title = f"All {n} countries score above the {AVG_LABEL}"
    else:
        verb = 'scores' if n_above == 1 else 'score'
        map_title = f"{n_above} of {n} countries {verb} above the {AVG_LABEL}"
    map_subtitle = f"{selected_region}, happiness score minus the {AVG_LABEL} of {avg_all:.2f}, 2023"

fig_map = px.choropleth(filtered,
                        locations='iso_alpha',
                        locationmode='ISO-3',
                        color='Score_vs_avg',
                        color_continuous_scale=[BELOW, MIDPOINT, ABOVE],
                        # A fixed range, symmetric around 0, puts the neutral colour exactly on the
                        # average and keeps colours comparable across filters.
                        # (color_continuous_midpoint would rescale per filter, and it has no
                        # effect once range_color is set.)
                        range_color=[-max_gap, max_gap],
                        hover_name='Country',
                        hover_data={'Score': ':.2f', 'Score_vs_avg': ':+.2f', 'iso_alpha': False},
                        labels={'Score': 'Happiness score', 'Score_vs_avg': f'vs {AVG_LABEL}'},
                        projection='natural earth',
                        template='plotly_white',
                        height=650)

CB_LEN = 0.5   # colour bar length as a share of the width; the end labels sit at its edges
CB_Y = -0.1    # colour bar top edge, below the map; the midpoint arrow points here

fig_map.update_layout(title=dict(text=map_title, subtitle=dict(text=map_subtitle)),
                      title_font=dict(family='Arial', size=13, color='slategrey'),
                      font=dict(family='Arial', size=12),
                      # no padding, so the bar starts and ends exactly where the labels say
                      coloraxis_colorbar=dict(orientation='h', x=0.5, xanchor='center',
                                              y=CB_Y, yanchor='top', len=CB_LEN, thickness=12,
                                              xpad=0, ypad=0, outlinewidth=0,
                                              title=dict(text='')),
                      margin=dict(l=0, r=0, t=80, b=95))

fig_map.update_geos(showframe=False, showcoastlines=False,
                    landcolor=NO_DATA, showcountries=True, countrycolor='white')
if all_regions:
    fig_map.update_geos(lataxis_range=[-56, 84])   # crop Antarctica, which has no data
else:
    fig_map.update_geos(fitbounds='locations')   # zoom to the selected region

fig_map.update_traces(marker_line_color='#AAAAAA', marker_line_width=0.3)

# label the midpoint of the colour scale, and both ends in their own colour
fig_map.add_annotation(xref='paper', yref='paper', x=0.5, y=CB_Y,
                       text=f"{AVG_LABEL} {avg_all:.2f}",
                       showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1, arrowcolor='#333333',
                       ax=0, ay=-22, font=dict(color='#333333', size=12))
fig_map.add_annotation(xref='paper', yref='paper', x=0.5 - CB_LEN / 2, y=CB_Y,
                       text="Below average", showarrow=False,
                       xanchor='left', yanchor='bottom', font=dict(color=BELOW, size=12))
fig_map.add_annotation(xref='paper', yref='paper', x=0.5 + CB_LEN / 2, y=CB_Y,
                       text="Above average", showarrow=False,
                       xanchor='right', yanchor='bottom', font=dict(color=ABOVE, size=12))


# ── Layout: full width, one chart under the other, so the world map stays readable ──
st.plotly_chart(fig, width='stretch')
st.plotly_chart(fig_map, width='stretch', config={'scrollZoom': False})   # page scroll should not zoom the map
grey_note = ("Grey countries are not in this dataset." if all_regions
             else f"Grey countries are outside {selected_region} or not in this dataset.")
st.caption(f"Colour shows each country's score minus {avg_all:.2f}, the average of all {len(df)} "
           f"countries in this dataset. Near-white countries are close to that average. {grey_note}")

st.divider()
st.caption("Built with Streamlit + Plotly")
