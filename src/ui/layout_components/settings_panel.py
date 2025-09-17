"""
Settings panel component for the sidebar.
"""

import streamlit as st

from ...utils.i18n import I18n


def render_settings_panel() -> None:
    """Render the settings panel in the sidebar."""
    st.header(I18n.t('settings'))
    
    # Language selection
    I18n.render_language_selector()