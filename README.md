# Krypto

## Descripción
Una aplicacion para jugar al juego de mesa de rapidez matematica llamado Krypto, en donde se presentaran 5 numeros. Usando obligatoriamente los 4 primeros y las operaciones matematicas basicas (sumar, restar, dividir y multiplicar) tienes que llegar al 5to numero. 

Un ejemplo: [1,2,3,4,5]
- Posible Solucion: "4+1-3-2"
+ Respuesta del Servidor: "CORRECTO"

- Posible Solucion: "2*4-3*1"
+ Respuesta del Servidor: "CORRECTO"

## Características
- Te puedes conectar al servidor principal usando IPv4 o IPv6 (depende de tu maquina)
- Crear servidores, eligiendo modo de juego y cantidad de jugadores maxima.
- Un sistema de validacion de solucion flexible y confiable.
- Varios modos de juegos, para jugar a Krypto como nunca antes [WORK IN PROGRESS]

## Uso básico
Se usa la terminal, asi que todos funciona en base a inputs basicos (El numero de una lista de opciones, "exit" o q para salir). El input mas complejo es la solucion del puzzle, que no es mas que una cuenta matematica de 4 nuemeros y 3 operaciones.

### Cliente
```bash
python client/user.py 
```

## Documentación adicional
Para más información, consulta los siguientes documentos:
- [INSTALL.md](INSTALL.md): Instrucciones detalladas de instalación
- [INFO.md](INFO.md): Información técnica y decisiones de diseño
- [TODO.md](TODO.md): Funcionalidades planificadas para el futuro
