from PyPDF2 import PdfMerger
import sys, os


#chemin du dossier contenant les pdf a fusionner
n = len(sys.argv)
if n <= 2:
    print("Nombre d'argument invalide : 'dossier contenant les pdf, nom du fichier en sortie'")
    sys.exit()

dir = os.getcwd()
input_dir = sys.argv[1]
file_name_output = sys.argv[2]

#Si le dossier contient un fichier pdf
contain_pdf = False

dir = os.path.join(dir, input_dir)

# Initialiser le PdfMerger
merger = PdfMerger()

# Ajouter les fichiers PDF à fusionner
for file in os.listdir(dir):
    if file.endswith(".pdf"):
        contain_pdf = True
        merger.append(os.path.join(dir, file))

if not contain_pdf:
    print("le dossier " + input_dir + " ne contient aucun fichier pdf")
    sys.exit()

# Écrire le fichier PDF fusionné dans un nouveau fichier
merger.write(file_name_output)
merger.close()