# Decisiones de Diseño

## Arquitectura general
La arquitectura del sistema está basada en una estructura cliente-servidor multinivel, donde cada componente principal interactúa a través de interfaces bien definidas. Los componentes principales incluyen el User (cliente), MainServer (servidor principal) y múltiples instancias de GameServer (servidores de juego).

## Tecnologías utilizadas
- **Lenguaje principal**: Python
- **Concurrencia**: async/await, threading, multiprocessing
- **Comunicación de red**: Sockets TCP
- **Almacenamiento de datos**: Estructuras de almacenamiento de python

## Decisiones clave y justificaciones

### Comunicación entre componentes
Se implementó un protocolo de comunicación basado en mensajes con formato delimitado por pipes (|) a través de sockets TCP.

**Justificación**: Los sockets proporcionan una comunicación eficiente y de bajo nivel, ideal para un juego que requiere respuestas rápidas. El formato de mensajes simple facilita el análisis y depuración.

### Gestión de concurrencia
Se utiliza async/await para manejar múltiples conexiones en el servidor principal, mientras que se emplean procesos separados para cada servidor de juego.

**Justificación**: async/await permite manejar eficientemente múltiples conexiones de clientes sin bloquear el hilo principal. Los procesos separados para cada servidor de juego aíslan las partidas y aprovechan mejor los sistemas multinúcleo.

### Modelo de datos
El modelo de datos está centrado en la representación en memoria de los juegos, puzzles y estados de los jugadores.

**Justificación**: Para un juego de cartas de cálculo mental y velocidad, mantener los datos en memoria proporciona la respuesta más rápida posible y simplifica la implementación.

### Manejo logs
Se implementa un sistema centralizado de registro y manejo de errores mediante la clase Logger que captura y registra todas las excepciones.

**Justificación**: Un sistema centralizado de logging facilita la depuración y el mantenimiento del sistema, permitiendo un seguimiento detallado de la comunicación entre componentes.

## Desafíos encontrados y soluciones
- **Desafío 1**: Sincronización entre múltiples jugadores en tiempo real
    - **Solución**: Implementación de un sistema de mensajería asíncrono que mantiene a todos los clientes actualizados sobre el estado del juego.

- **Desafío 2**: Escalabilidad del sistema para múltiples partidas simultáneas
    - **Solución**: Arquitectura de procesos independientes para cada servidor de juego, coordinados por un servidor principal.

## Seguridad
Se implementaron medidas básicas de seguridad como validación de entradas y protección contra intentos de manipulación de la comunicación entre cliente y servidor.

## Rendimiento
El sistema está optimizado para proporcionar tiempos de respuesta rápidos, esenciales en un juego de velocidad mental, mediante el uso eficiente de recursos del sistema y la minimización de la latencia de red.
