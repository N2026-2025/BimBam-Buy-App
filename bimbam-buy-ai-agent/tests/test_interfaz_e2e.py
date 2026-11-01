import re
from playwright.sync_api import Page, expect

def test_streamlit_interface(page: Page):
    # Intentar conectarse al servidor local levantado por GitHub Actions
    page.goto("http://localhost:8501")
    
    # Verificar que el título de la página o la app contenga texto relacionado al agente
    expect(page).to_have_title(re.compile("Streamlit", re.IGNORECASE))
