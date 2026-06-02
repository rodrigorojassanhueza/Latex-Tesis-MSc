# Presentación de defensa

Carpeta creada para la presentación Beamer de defensa de tesis. No modifica los archivos fuente de la tesis.

## Compilación

Desde esta carpeta:

```powershell
latexmk -pdf main.tex
```

Para limpiar auxiliares:

```powershell
latexmk -c main.tex
```

También puede usarse:

```powershell
make
```

## Dependencias LaTeX

Usa paquetes comunes de LaTeX/Beamer:

- `beamer`
- `babel`
- `graphicx`
- `booktabs`
- `tabularx`
- `array`
- `textcomp`
- `tikz`
- `etoolbox`
- `url`
- `apacite`
- `lmodern`

La bibliografía se compila con BibTeX mediante `apacite_noinitials.bst`, incluido localmente para reproducir el estilo APA usado por la tesis.

## Estructura

- `main.tex`: fuente Beamer 16:9 con 23 diapositivas numeradas de exposición, 5 anexos no numerados y 4 diapositivas de referencias APA.
- `main.pdf`: PDF compilado.
- `guion_presentacion.md`: guion oral por diapositiva, con tiempos y transiciones.
- `figures/`: copias locales de figuras seleccionadas desde la tesis, incluidas en el cuerpo principal las figuras obligatorias 4.2, 4.3, 5.18, 5.22, 5.30, 5.41, 5.42 y 5.43.
- `figures/uchile2.pdf`: logo de portada usado por la tesis.
- `references.bib`: copia local de `library.bib`.
- `references_nocite.tex`: lista de las 60 referencias efectivamente presentes en la bibliografía de la tesis con datos privados.
- `apacite_noinitials.bst`: estilo APA usado para generar las referencias.
- `Makefile`: compilación con `latexmk`.

## Figuras reutilizadas

Las figuras copiadas provienen de `figuras_tesis/` y se usan como apoyo visual. En la presentación no se muestran líneas de fuente bajo las figuras; cada figura o tabla tiene un caption explicativo.

- `trazas_fsr.png`: traza/modelos de ruptura FSR.
- `modelo_subduccion.pdf`: modelo de subducción.
- `exposicion_composicion.pdf`: exposición por tipología.
- `fig_4_3_arbol_logico_tikz.tex`: Figura 4.3 de la versión con datos privados, reproducida como TikZ en la diapositiva 10.
- `fig_4_2_escenarios_simulados.pdf`: geometrías deterministas de FSR, interplaca e intraplaca.
- `fig_5_18_psha_curvas_pga_poisson.pdf`: curvas de amenaza de PGA, modelo Poisson.
- `fig_5_22_disagg_pga_poisson.pdf`: desagregación de PGA por fuente, modelo Poisson.
- `fig_5_30_perdidas_comuna_materialidad.pdf`: exposición, materialidad y pérdidas por comuna.
- `fig_5_41_aalr_cambio_rel_pct.pdf`: cambio relativo porcentual en AALR.
- `fig_5_42_oep_relativo.pdf`: curvas OEP relativas con y sin FSR.
- `fig_5_43_lambda_con_sin_fsr.pdf`, `fig_5_43_delta_lambda.pdf`: tasas de excedencia de pérdida y diferencia al incorporar FSR.
- `dsha_inter_pga.pdf`, `dsha_fsr_pga.pdf`, `dsha_intra_pga.pdf`: mapas DSHA de PGA.
- Figuras de anexo: convergencia de árbol lógico, convergencia de GMFs, curvas de vulnerabilidad y resultados BPT representativos. No repiten figuras usadas en el cuerpo principal.

## Notas de contenido

- Documento base usado: `main_con_datos_privados.tex`, que incluye `main.tex`.
- La presentación tiene 23 diapositivas numeradas de exposición, 5 diapositivas no numeradas de anexo y 4 diapositivas no numeradas de referencias APA.
- Las diapositivas de anexo y referencias no cuentan dentro de las 23 diapositivas de exposición.
- Las figuras principales tienen numeración independiente de las tablas; los anexos usan numeración `Figura A.n` y `Tabla A.n`.
- Los captions de tablas se ubican arriba de la tabla y los captions de figuras debajo de la imagen.
- Se fuerza tamaño 16:9 horizontal (`160 mm x 90 mm`) y `Page rot: 0` para evitar rotación de páginas en el PDF.
- Se cambió el artículo a `el PGA` donde corresponde.
- Se incorporaron las ecuaciones BPT en el cuerpo metodológico.
- Las cifras de exposición, pérdidas, AAL/AALR y contribuciones de fuente fueron tomadas de la tesis.
- No se detectaron datos faltantes de portada ni marcadores pendientes.
