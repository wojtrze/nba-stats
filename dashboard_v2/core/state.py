"""Choices that should survive switching pages. Streamlit drops a widget's state when its page isn't shown, so
each persistent widget keeps a copy under '_<key>' and is restored from it."""
from typing import List, Tuple

import streamlit as st

import i18n
from espn_scraper import CURRENT_SEASON, SEASONS
from loaders import season_label
from models import DEFAULT_SEASON_TYPES

SEASON_TYPE_LABELS = {'pre': "Preseason", 'regular': "Regular season", 'playin': "Play-in", 'post': "Playoffs"}


def type_label(season_type: str) -> str:
    return i18n.t(f'type.{season_type}', language())


def persist(key: str, default):
    """Restore the widget `key` before it's drawn; pass on_change=remember, args=(key,) to the widget."""
    st.session_state[key] = st.session_state.get(f"_{key}", default)


def remember(key: str):
    st.session_state[f"_{key}"] = st.session_state[key]


def language() -> str:
    """The language the pages are shown in ('en' / 'pl'), chosen in the sidebar (language_picker)."""
    return st.session_state.get('_language', i18n.DEFAULT)


def language_picker():
    """The language switch, drawn where it's called (the sidebar)."""
    persist('language', i18n.DEFAULT)
    st.segmented_control(i18n.t('language', language()), list(i18n.LANGS), format_func=i18n.LANGUAGE_NAMES.get,
                         key='language', on_change=remember, args=('language',), label_visibility='collapsed')
    if not st.session_state.get('language'):           # a click on the selected option clears it: keep it
        st.session_state['language'] = st.session_state['_language'] = language()


def scope() -> Tuple[List[int], List[str]]:
    """The seasons and game types the analysis uses, without drawing anything."""
    seasons = st.session_state.get('_scope_seasons', [CURRENT_SEASON])
    types = st.session_state.get('_scope_types', DEFAULT_SEASON_TYPES)
    return seasons or [CURRENT_SEASON], types or DEFAULT_SEASON_TYPES


def scope_label() -> str:
    seasons, types = scope()
    return (", ".join(season_label(s) for s in sorted(seasons)) + " · "
            + (", ".join(type_label(t).lower() for t in types) if len(types) < 4
               else i18n.t('scope.all_types', language())))


def scope_picker():
    """The seasons and game-type pickers, drawn where it's called (the header's Scope popover)."""
    persist('scope_seasons', [CURRENT_SEASON])
    persist('scope_types', DEFAULT_SEASON_TYPES)
    lang = language()
    st.multiselect(i18n.t('scope.seasons', lang), sorted(SEASONS, reverse=True), key='scope_seasons',
                   format_func=season_label, on_change=remember, args=('scope_seasons',),
                   help=i18n.t('scope.seasons_help', lang))
    st.pills(i18n.t('scope.types', lang), list(SEASON_TYPE_LABELS), key='scope_types', selection_mode='multi',
             format_func=type_label, on_change=remember, args=('scope_types',), help=i18n.t('scope.types_help', lang))
    st.caption(i18n.t('scope.every_page', lang))
