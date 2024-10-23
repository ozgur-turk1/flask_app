import base64
from io import BytesIO
import logging
from flask import Flask, redirect, render_template, request, send_file, session, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from werkzeug.utils import secure_filename
import PyPDF2
import os
import json
import qrcode
from dotenv import load_dotenv


logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

load_dotenv()  # Charger les variables depuis le fichier .env

app = Flask(__name__, template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key_if_not_set')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def check_password(self, password):
        return self.password == password


@login_manager.user_loader
def load_user(user_id):
    with open('users.json') as f:
        users = json.load(f)
    return User(users[str(user_id)]['id'], users[str(user_id)]['username'], users[str(user_id)]['password'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with open('users.json') as f:
            users = json.load(f)
        for user in users.values():
            if user['username'] == username and user['password'] == password:
                logging.info(f'Utilisateur {username} connecté')
                login_user(load_user(user['id']))
                return redirect(url_for('index'))
            
        logging.info(f'Nom d\'utilisateur {username} ou mot de passe incorrect')
        return 'Nom d\'utilisateur ou mot de passe incorrect'
    else:
        return render_template('login.html')

@app.route('/')
@login_required
def index():
    logging.info("Accès à la page d'accueil")
    return render_template('index.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/fusion', methods=['GET', 'POST'])
def merge():
    if request.method == 'POST':
        pdf_files = request.files.getlist('files')
        pdf_merger = PyPDF2.PdfMerger()

        for pdf in pdf_files:
            pdf_path = os.path.join('uploads', secure_filename(pdf.filename))
            pdf.save(pdf_path)
            pdf_merger.append(pdf_path)
            logging.info(f'Fichier {pdf.filename} ajouté à la fusion')

        output_path = 'merged.pdf'
        with open(output_path, 'wb') as f:
            pdf_merger.write(f)
        logging.info(f'Fichier fusionné créé à {output_path}')

        #TODO
        # Supprimer les fichiers après la fusion
        # for pdf in pdf_files:
        #     os.remove(os.path.join('uploads', secure_filename(pdf.filename)))
        #     logging.info(f'Fichier {pdf.filename} supprimé')

        return send_file(output_path, as_attachment=True)
    else:
        return render_template('merge.html')



# Fonction réutilisable pour créer un QR Code
def create_qrcode(url):
    logging.info(f"Génération du QR Code pour l'URL : {url}")
    img = qrcode.make(url)
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)  # Revenir au début du fichier pour la lecture
    logging.info(f"QR Code généré avec succès pour l'URL : {url}")
    return img_io

# Page pour générer un QR Code et l'afficher
@app.route('/qrcode', methods=['GET', 'POST'])
@login_required
def generate_qrcode():
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            logging.info(f"Réception de l'URL pour générer le QR Code : {url}")
            
            # Générer le QR Code une seule fois et le stocker en session
            try:
                img_io = create_qrcode(url)
                session['qrcode_image'] = base64.b64encode(img_io.getvalue()).decode('utf-8')  # Stocker en session
                session['qrcode_url'] = url  # Stocker aussi l'URL pour le téléchargement
                logging.info(f"QR Code pour l'URL {url} stocké en session.")
            except Exception as e:
                logging.error(f"Erreur lors de la génération du QR Code pour l'URL {url}: {e}")
                return "Une erreur est survenue lors de la génération du QR Code.", 500

            return redirect(url_for('display_qrcode'))
        else:
            logging.warning("Aucune URL fournie pour la génération du QR Code.")
            return "Veuillez entrer un lien valide.", 400
    logging.info("Accès à la page de génération de QR Code")
    return render_template('qrcode.html')

# Afficher le QR Code sur la page après la génération
@app.route('/display_qrcode')
@login_required
def display_qrcode():
    qrcode_data = session.get('qrcode_image')
    url = session.get('qrcode_url')
    if qrcode_data and url:
        logging.info(f"Affichage du QR Code pour l'URL {url}")
        return render_template('qrcode.html', qrcode_data=qrcode_data, url=url)
    else:
        logging.warning("Tentative d'accès à l'affichage du QR Code sans données en session.")
        return redirect(url_for('generate_qrcode'))

# Route pour télécharger le QR Code
@app.route('/download_qrcode', methods=['POST'])
@login_required
def download_qrcode():
    qrcode_data = session.get('qrcode_image')
    url = session.get('qrcode_url')

    if qrcode_data and url:
        logging.info(f"Téléchargement du QR Code pour l'URL {url}")
        # Convertir les données du QR Code stocké en binaire
        img_io = BytesIO(base64.b64decode(qrcode_data))
        return send_file(img_io, mimetype='image/png', as_attachment=True, download_name='qrcode.png')
    else:
        logging.warning("Tentative de téléchargement du QR Code sans données valides en session.")
        return redirect(url_for('generate_qrcode'))


if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)  # Accessible depuis l'extérieur