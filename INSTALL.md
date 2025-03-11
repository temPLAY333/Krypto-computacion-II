# Instalación y Despliegue

## Requisitos previos
- Python 3.11 o superior
- [Otros requisitos de software...]

## Instalación desde el repositorio

### Clonar el repositorio
```bash
git clone https://github.com/temPLAY333/Krypto-computacion-II.git
cd Krypto
```

### Configuración del entorno virtual (recomendado)
```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
venv\Scripts\activate     # En Windows
```

### Instalar dependencias
```bash
pip install -r requirements.txt
```

## Ejecución Del Servidor (MainServer)
```bash
python puzzle/main_server.py [argumentos]
```

## Ejecución Del Usuario (User)
```bash
python cliente/user.py 
```

## Despliegue en producción
- Se utiliza la libreria *parser*, y MainServer toma los siguientes argumentos
- --debug: Activa los logs.debug, para mayor informacion sobre el funcionamiento interno a la hora de ejecutar el servidor.
