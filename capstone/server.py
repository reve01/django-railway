from waitress import serve
from capstone.wsgi import application  # Importa la aplicación de Django

serve(application, host='0.0.0.0', port=8080)