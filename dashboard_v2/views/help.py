"""How to read this: what the numbers mean and how to choose a bet, in plain words (i18n.TEXTS 'help.*'), and every
column's explanation from i18n.TERMS, the same text as the tooltips."""
import streamlit as st

import i18n
from core.columns import PROPS_MAIN, PROPS_MORE
from core.state import language
from core.ui import page_header
from i18n import t

lang = language()
page_header(t('help.title', lang), t('help.purpose', lang))

with st.container(border=True):
    st.markdown(f"#### {t('help.steps.title', lang)}")
    st.markdown(t('help.steps.body', lang))

for section in ('odds', 'margin', 'chance', 'edge', 'signals', 'flags', 'verdict', 'player'):
    st.markdown(f"#### {t(f'help.{section}.title', lang)}")
    st.markdown(t(f'help.{section}.body', lang))

st.markdown(f"#### {t('help.glossary.title', lang)}")
st.caption(t('help.glossary.caption', lang))
for column in PROPS_MAIN + [c for c in PROPS_MORE if c not in PROPS_MAIN]:
    if i18n.term(column):
        with st.expander(i18n.label(column, lang)):
            st.markdown(i18n.tooltip(column, lang))
