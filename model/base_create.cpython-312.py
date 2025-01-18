import sqlite3
import os
import secrets
import time

def crear_tablas_servidor(server_id):
    db_path = f"server/discord_bot_{server_id}.db"
    
    # Crear carpeta si no existe
    if not os.path.exists("server"):
        os.makedirs("server")

    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tabla de Configuración
    cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS Configuracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prefix TEXT DEFAULT '!',  -- Prefijo predeterminado
            moderacion_activada INTEGER DEFAULT 1,  -- Usar INTEGER en lugar de BOOLEAN
            experiencia_activada INTEGER DEFAULT 1,  -- Usar INTEGER en lugar de BOOLEAN
            bienvenida_url TEXT,
            despedida_url TEXT,
            canal_id_b_g INTEGER  -- Nuevo campo para almacenar el ID del canal
        )
    """)

    # Tabla de Moderación (Configuración global de moderación)
    cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS Moderacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warns INTEGER DEFAULT 3,            -- Número de advertencias para sancionar
            duracion_warn INTEGER DEFAULT 300   -- Duración en segundos del muteo
        )
    """)

    # Tabla de Palabras de Moderación (Palabras específicas para la moderación)
    cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS PalabrasModeracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            palabra_clave TEXT UNIQUE  -- Palabra clave que será monitoreada
        )
    """)

    # Tabla de Usuarios (Para llevar el registro de advertencias de los usuarios)
    cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            warns INTEGER DEFAULT 0
        )
    """)

    # Tabla de Usuarios (Para llevar el registro de experiencia de los usuarios)
    cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS Experiencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,           -- ID del usuario
            total_exp INTEGER DEFAULT 0,        -- Puntos de experiencia acumulados
            nivel INTEGER DEFAULT 0,            -- Nivel calculado basado en la experiencia
            mensaje_contado INTEGER DEFAULT 0,  -- Contador de mensajes enviados
            ultima_interaccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Última vez que interactuó
            canal_id INTEGER DEFAULT NULL       -- ID del canal para enviar mensajes
        )
    """)

    # Tabla para almacenar los tokens generados
    cursor.execute(""" 
        CREATE TABLE IF NOT EXISTS Tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_expiracion TIMESTAMP
        )
    """)

    # Confirmar cambios y cerrar conexión
    conn.commit()
    conn.close()

    print(f"Base de datos creada para el servidor: {server_id}")


# Función para generar un token y almacenarlo en la base de datos
def generar_token(server_id):
    # Generar un token único
    token = secrets.token_hex(16)  # 32 caracteres hexadecimales
    
    # Calcular la fecha de expiración (1 minuto desde ahora)
    fecha_expiracion = time.time() + 60  # 60 segundos = 1 minuto

    # Conectar a la base de datos
    db_path = f"server/discord_bot_{server_id}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insertar el token en la base de datos
    cursor.execute(""" 
        INSERT INTO Tokens (token, fecha_expiracion) 
        VALUES (?, ?)
    """, (token, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(fecha_expiracion))))

    # Confirmar cambios y cerrar conexión
    conn.commit()
    conn.close()

    return token


# Función para verificar si un token es válido (no ha expirado)
def verificar_token(server_id, token):
    db_path = f"server/discord_bot_{server_id}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(""" 
        SELECT fecha_expiracion FROM Tokens WHERE token = ?
    """, (token,))
    resultado = cursor.fetchone()

    if resultado is None:
        conn.close()
        return False

    fecha_expiracion = time.mktime(time.strptime(resultado[0], '%Y-%m-%d %H:%M:%S'))
    if time.time() > fecha_expiracion:
        # Borrar el token después de que haya expirado
        cursor.execute("DELETE FROM Tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return False

    conn.close()
    return True