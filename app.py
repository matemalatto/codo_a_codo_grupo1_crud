#--------------------------------------------------------------------
# Instalar con pip install Flask
from flask import Flask, request, jsonify

# Instalar con pip install flask-cors
from flask_cors import CORS

# Instalar con pip install mysql-connector-python
import mysql.connector

# Si es necesario, pip install Werkzeug
from werkzeug.utils import secure_filename

# No es necesario instalar, es parte del sistema estándar de Python
import os
import time
#--------------------------------------------------------------------

# Creo instancia de la Clase Flask
app = Flask(__name__)
CORS(app)  # Esto habilitará CORS para todas las rutas

class Catalogo:
    # Constructor de la clase Catalogo
    def __init__(self, host, user, password, database):
        # Establecer conexión con la base de datos
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password
        )
        self.cursor = self.conn.cursor()
        
        # Intentar seleccionar la base de datos, o crearla si no existe
        try:
            self.cursor.execute(f"USE {database}")
        except mysql.connector.Error as err:
            if err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
                self.cursor.execute(f"CREATE DATABASE {database}")
                self.conn.database = database
            else:
                raise err
        
        # Crear la tabla 'destinos' si no existe
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS destinos (
            codigo INT AUTO_INCREMENT PRIMARY KEY,
            pais VARCHAR(255) NOT NULL,
            ciudad VARCHAR(255) NOT NULL,
            precio DECIMAL(10, 2) NOT NULL,
            imagen_url VARCHAR(255))''')
        self.conn.commit()
        
        # Cerrar el cursor inicial y abrir uno nuevo con el parámetro dictionary=True
        self.cursor.close()
        self.cursor = self.conn.cursor(dictionary=True)

    def listar_destinos(self):
        # Obtener todos los destinos de la tabla
        self.cursor.execute("SELECT * FROM destinos")
        destinos = self.cursor.fetchall()
        return destinos
    
    def consultar_destino(self, codigo):
        # Consultar un destino por su código
        self.cursor.execute(f"SELECT * FROM destinos WHERE codigo = {codigo}")
        return self.cursor.fetchone()

    def agregar_destino(self, pais, ciudad, precio, imagen):
        # Agregar un nuevo destino a la tabla
        sql = "INSERT INTO destinos (pais, ciudad, precio, imagen_url) VALUES (%s, %s, %s, %s)"
        valores = (pais, ciudad, precio, imagen)
        self.cursor.execute(sql, valores)
        self.conn.commit()
        return self.cursor.lastrowid

    def modificar_destino(self, codigo, nuevo_pais, nueva_ciudad, nuevo_precio, nueva_imagen):
        # Modificar un destino existente en la tabla
        sql = "UPDATE destinos SET pais = %s, ciudad = %s, precio = %s, imagen_url = %s WHERE codigo = %s"
        valores = (nuevo_pais, nueva_ciudad, nuevo_precio, nueva_imagen, codigo)
        self.cursor.execute(sql, valores)
        self.conn.commit()
        return self.cursor.rowcount > 0

    def eliminar_destino(self, codigo):
        # Eliminar un destino de la tabla por su código
        self.cursor.execute(f"DELETE FROM destinos WHERE codigo = {codigo}")
        self.conn.commit()
        return self.cursor.rowcount > 0

#--------------------------------------------------------------------
# Cuerpo del programa
#--------------------------------------------------------------------
# Crear una instancia de la clase Catalogo
# Cambiar los parámetros de conexión según tu configuración de MySQL
catalogo = Catalogo(host='localhost', user='root', password='', database='mundiviajes')

# Carpeta para guardar las imágenes de los destinos
ruta_destino = './static/imagenes/'
#ruta_destino = '/home/juanpablocodo/mysite/static/imagenes/'

@app.route("/destinos", methods=["GET"])
def listar_destinos():
    # Endpoint para obtener todos los destinos
    destinos = catalogo.listar_destinos()
    return jsonify(destinos)

@app.route("/destinos/<int:codigo>", methods=["GET"])
def mostrar_destino(codigo):
    # Endpoint para obtener un destino específico por su código
    destino = catalogo.consultar_destino(codigo)
    if destino:
        return jsonify(destino)
    else:
        return "Destino no encontrado", 404

@app.route("/destinos", methods=["POST"])
def agregar_destino():
    # Endpoint para agregar un nuevo destino
    pais = request.form['pais']
    ciudad = request.form['ciudad']
    precio = request.form['precio']
    imagen = request.files['imagen']
    nombre_imagen = secure_filename(imagen.filename)
    nombre_base, extension = os.path.splitext(nombre_imagen)
    nombre_imagen = f"{nombre_base}_{int(time.time())}{extension}"

    nuevo_codigo = catalogo.agregar_destino(pais, ciudad, precio, nombre_imagen)
    if nuevo_codigo:
        imagen.save(os.path.join(ruta_destino, nombre_imagen))
        return jsonify({"mensaje": "Destino agregado correctamente.", "codigo": nuevo_codigo, "imagen": nombre_imagen}), 201
    else:
        return jsonify({"mensaje": "Error al agregar el destino."}), 500

@app.route("/destinos/<int:codigo>", methods=["PUT"])
def modificar_destino(codigo):
    # Endpoint para modificar un destino existente
    nuevo_pais = request.form.get("pais")
    nueva_ciudad = request.form.get("ciudad")
    nuevo_precio = request.form.get("precio")

    destino = catalogo.consultar_destino(codigo)
    if not destino:
        return jsonify({"mensaje": "Destino no encontrado"}), 404

    # Manejar la nueva imagen si se ha proporcionado
    if 'imagen' in request.files and request.files['imagen'].filename != '':
        imagen = request.files['imagen']
        nombre_imagen = secure_filename(imagen.filename)
        nombre_base, extension = os.path.splitext(nombre_imagen)
        nombre_imagen = f"{nombre_base}_{int(time.time())}{extension}"
        
        # Eliminar la imagen anterior si existe
        imagen_vieja = destino["imagen_url"]
        if imagen_vieja:
            ruta_imagen_vieja = os.path.join(ruta_destino, imagen_vieja)
            if os.path.exists(ruta_imagen_vieja):
                os.remove(ruta_imagen_vieja)
        
        # Guardar la nueva imagen
        imagen.save(os.path.join(ruta_destino, nombre_imagen))
    else:
        nombre_imagen = destino["imagen_url"]

    # Actualizar los datos del destino en la base de datos
    if catalogo.modificar_destino(codigo, nuevo_pais, nueva_ciudad, nuevo_precio, nombre_imagen):
        return jsonify({"mensaje": "Destino modificado correctamente"}), 200
    else:
        return jsonify({"mensaje": "Error al modificar el destino"}), 500

@app.route("/destinos/<int:codigo>", methods=["DELETE"])
def eliminar_destino(codigo):
    # Endpoint para eliminar un destino por su código
    destino = catalogo.consultar_destino(codigo)
    if destino:
        ruta_imagen = os.path.join(ruta_destino, destino['imagen_url'])
        if os.path.exists(ruta_imagen):
            os.remove(ruta_imagen)

        if catalogo.eliminar_destino(codigo):
            return jsonify({"mensaje": "Destino eliminado"}), 200
        else:
            return jsonify({"mensaje": "Error al eliminar el destino"}), 500
    else:
        return jsonify({"mensaje": "Destino no encontrado"}), 404

if __name__ == "__main__":
    app.run(debug=True)
