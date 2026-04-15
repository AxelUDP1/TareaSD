Tarea Sistemas Distribuidos



Contexto: Las empresas de transportes en general quieren saber cuantos edificios hay en una zona, cuantas área construida hay y que tan densa es una zona esto mediante el dataset de Google open buildings que contiene info de ubicación tamaño y nivel de confianza de edificios mediante imágenes satelitales. 



Problema: Muchas empresas hacen consultas al mismo tiempo y muchas consultas repiten lo mismo



Esto causa que cada consulta tarde un tiempo y el sistema se vuelva lento



Solución: Optimizar las consultas a los datos a través del diseño de un sistema distribuido que incorpore mecanismos de caché para optimizar el acceso a la información, reducir la latencia de respuesta y mejorar el rendimiento del sistema bajo distintos patrones de carga



El caché hace que llegue la consulta y pregunta si ya lo tiene guardado:

&#x09;Si la respuesta es si (Hit): lo devuelve (Rápido)

&#x09;Si la respuesta es no (Miss): Lo calcula y lo guarda (Lento)



En base a esto se construira:



1\. Generador de trafico: Simulará a los usuarios preguntando cosas

2\. Caché(redis): Guarda las respuestas

3\. Generador de respuestas(Queries): Procesador que calcula los resultados

4\. Almacenamiento de métricas: Mide que tan bien funciona todo Registra hits, misses, latencias, throughput y tasa de evicción.



Construccion del sistema:



Archivos:

data/ --> Aquí va el dataset de edificios

&#x09;- building.csv

Src/ --> lugar donde va todo el código

&#x09;- cache.py --> maneja el caché (redis)

&#x09;- data\_loader.py --> carga el dataset

&#x09;- main.py --> Ejecuta todo el flujo

&#x09;- metrics\_collector.py --> guarda metricas

&#x09;- query\_processor.py --> calcula Q1-Q5

&#x09;- traffic\_generator.py --> Genera las consultas
results/ --> Aquí se guardan los resultados



docker-compose.yml --> Levanta todo el sistema (la app y redis(caché))



dockerfile --> Define como construir la app (Python+librerias) (Para que corra el cualquier PC igual)



README.md --> Explica como ejecutar el proyecto

requeriments.txt --> Lista de librerías Python necesarias.



\---------------------------------------------------



Creamos Traffic\_generator.py dentro de la carpeta src/

* Generamos consultas con distribución Zipf y uniforme



Creamos query\_proccesor dentro de la carpeta src/

1. Se crean 5 tipos de consultas

   * Q1: Conteo de edificios en una zona
   * Q2: Area promedio y total para saber cuanto espacio construido hay en una zona
   * Q3: Densidad de edificios calculando cuantos edificios hay por KM cuadrado (cantidad/área)
   * Q4: Comparación de densidad, compara las zonas y dice cual es mas densa
   * Q5: Distribución de confianza, divide los valores de confianza en rangos y cuenta cuantos hay en cada uno
2. Calcula las respuestas de las consultas para saber si hay un miss



Creamos data\_loader.py dentro de la carpeta src/

&#x20;para cargar correctamente el dataset csv



Creamos metrics.py dentro de la carpeta src/

* Para medir hit rate, throughtput y latencia
* Dentro de este va guardando registros de cada consulta
* Metricas:

  * Hit rate: proporción de consultas respondidas desde caché.
  * Miss rate: proporción de consultas que no estaban en caché y debieron calcularse.
  * Throughput: cantidad de consultas procesadas por segundo.
  * Latency p50: tiempo de respuesta que deja al 50% de las consultas por debajo de ese valor.
  * Latency p95: tiempo de respuesta que deja al 95% de las consultas por debajo de ese valor.
  * Evictions: cantidad total de elementos expulsados de la caché.
  * Eviction rate: cantidad de expulsiones por minuto.
  * Cache efficiency: medida simple de beneficio de la caché comparando hits rápidos contra misses costosos.
  * Total requests: cantidad total de consultas ejecutadas.
  * Hits: cantidad total de cache hits.
  * Misses: cantidad total de cache misses.



Creamos cache.py dentro de la carpeta src/

Aquí implementamos el cache en redis que soporta ttl y políticas de evicción.



Creamos main.py dentro de la carpeta src/

Archivo donde unimos todo para:

  1. &#x09;cargar datos
  2. generar consultas
  3. buscar en caché
  4. si hay miss, ejecutar consulta
  5. guardar resultado en caché
  6. registrar métricas
  7. mostrar resumen final



Cargaremos el dataset Google Open Buildings

Se creo cut\_dataset.py para cortar en 10k de filas



Se creo plot\_results.py para generar graficos

&#x09;

