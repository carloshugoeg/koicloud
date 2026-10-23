# Node-agent como proceso aparte

## Status

Accepted. A-04.

## Context

El socket de Docker puede crear y borrar contenedores. Si la API abre ese socket, un request con un bug lo alcanza. Reiniciar la API no tiene que parar los ponds que ya corren.

## Decision

El node-agent es un proceso systemd, fuera de la API. Solo ese proceso abre el socket. La API le entrega jobs por loopback, con el header `X-Node-Token`.

## Consequences

Hay dos procesos que vigilar. La API puede reiniciar y los contenedores siguen. Si el agente está caído, los jobs quedan en cola hasta que vuelve.
