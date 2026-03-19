@echo off
echo Starting TCET Chatbot Frontend (Streamlit)...
echo.

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo Frontend will be available at: http://localhost:8501
echo.

streamlit run streamlit_app.py --server.port 8501
