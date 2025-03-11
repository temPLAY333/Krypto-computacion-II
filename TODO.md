# Mejoras Futuras y Pendientes

## Funcionalidades planificadas

### Optimizaciones Generales
- Validacion: Darle un mejor feedback al usuario en cuanto sus respuestas incorrectas. 
- Interfaz: Mejorar la fluidez del traspaso de UserInterface a PlayerInterface, y viceversa.
- Modularizacion de MainServer: MainServer deberia dividirse en 3 archivos; Main, ClientManager y ServerManager
- GameServer: Revisar funciones y responsabilidades de la superclase y las subclases, y recolocarles o mejorarlas segun sea pertinente.

## Mejoras menores
- Cambiar y mejorar el sistema de import de funciones, clases, librerias, etc.
- Hacer el Tutorial mas extensivo y explicativo.
- Revisar y eliminar funciones que no se usen, respetando las responsbilidades de clase.
- Revisar el modulo Messages y sus distintas clases, en busca de mayor modularizacion.

## Posibles adiciones
- CompetiveMode: Agregar un modo de duelo entre dos jugadores, que gane el que resuelva mas rapido X puzzles dados.
- SoloMode: Agregar un modo de juego en solitario, que mida el tiempo del jugador en X puzzles.

## Errores a solucionar
- Al salir de un GameServer, el socket se cierra mal. Revisar y solucionar.

## Notas adicionales
[Cualquier información adicional sobre el futuro del proyecto]
