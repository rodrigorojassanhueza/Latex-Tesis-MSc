# LATEX_TESIS

Proyecto LaTeX de la tesis **"Estudio de amenaza y vulnerabilidad sísmica de Falla San Ramón"**.
El documento usa el template de tesis de Pablo Pizarro y está organizado en archivos por capítulo.

## Archivos principales

- `main.tex`: archivo principal. Define portada, datos del documento, resumen, agradecimientos, configuración extra y el orden de inclusión de capítulos.
- `main_con_datos_privados.tex`: wrapper que compila `main.tex` incluyendo los bloques marcados como privados.
- `main_sin_datos_privados.tex`: wrapper que define `\omitprivatedata` antes de cargar `main.tex`; omite los bloques controlados por `\ifincludeprivatedata`.
- `template.tex`: template base de tesis.
- `template_config.tex`: configuración del template, estilos, captions, índices, bibliografía e imágenes.
- `library.bib`: base bibliográfica.
- `cap10_referencias.tex`: inserta la bibliografía con `\bibliography{library}`.

## Capítulos

- `cap1_introduccion.tex`: introducción, hipótesis, objetivos y estructura.
- `cap2_marco_teorico.tex`: amenaza y riesgo sísmico.
- `cap3_contexto_geologico.tex`: contexto geológico, condiciones de suelo y sismicidad.
- `cap4_metodologia.tex`: flujo metodológico, modelos de entrada, amenaza y riesgo con OpenQuake.
- `cap5_resultados.tex`: resultados de amenaza y riesgo sísmico.
- `cap7_discusion.tex`: discusión, conclusiones, limitaciones y proyecciones.
- `Anexos.tex`: material suplementario; actualmente no está incluido directamente desde `main.tex`.

## Carpetas

- `figuras_tesis/`: figuras usadas en la tesis, separadas por tema (`contexto_geologico`, `metodologia`, `resultados_amenaza`, `resultados_perdida`, etc.).
- `figs/tikz/`: fuentes TikZ, por ejemplo `fig_flujo_metodologico.tikz`.
- `img/`: imágenes del template, logos y ejemplos; es la carpeta raíz de imágenes configurada en `template_config.tex`.
- `Correcciones/`: PDFs con correcciones o revisiones externas.
- `_graph_generation_work/` y `_graph_generation_logs/`: salidas auxiliares de generación/postproceso de figuras.

## Scripts auxiliares

- `postprocess_resultado_perdida_svgs.py`: postprocesa SVGs de resultados de pérdida, los ajusta y exporta a PDF usando Inkscape.
- `run_selected_notebook_cells.py`: ejecuta celdas específicas de un notebook `.ipynb` desde línea de comandos.

## Compilación

Con `latexmk`:

```powershell
latexmk -pdf main.tex
latexmk -pdf main_sin_datos_privados.tex
latexmk -pdf main_con_datos_privados.tex
```

Sin `latexmk`, usar el flujo clásico sobre el archivo deseado:

```powershell
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Los archivos generados por LaTeX (`.aux`, `.bbl`, `.log`, `.toc`, `.lof`, `.lot`, `.pdf`, etc.) están listados en `.gitignore` y no deberían editarse manualmente.
