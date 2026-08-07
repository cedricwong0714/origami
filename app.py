"""
ORIGAMI Streamlit entrypoint.

From the repository root:

    pip install -e ".[ui]"
    streamlit run app.py
"""

from src.ui.streamlit_app import run

if __name__ == "__main__":
    run()
