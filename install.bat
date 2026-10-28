@echo off
chcp 65001 >nul
echo Установка библиотек для 1С AI Ассистента...
echo.
python -m pip install datasets --quiet
echo datasets installed
python -m pip install huggingface_hub --quiet
echo huggingface_hub installed
python -m pip install sentence-transformers --quiet
echo sentence-transformers installed
python -m pip install chromadb --quiet
echo chromadb installed
python -m pip install requests --quiet
echo requests installed
echo.
echo Все библиотеки установлены!
pause