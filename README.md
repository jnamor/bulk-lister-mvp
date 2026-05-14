# Créer un environnement virtuel (bonne pratique)
python -m venv venv

# L'activer
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Installer les dépendances
pip install -r requirements.txt

python3 main.py