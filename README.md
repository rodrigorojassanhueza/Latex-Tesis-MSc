# LATEX_TESIS

Proyecto LaTeX de la tesis **"Estudio de amenaza y vulnerabilidad sismica de Falla San Ramon"** y de la presentacion de defensa asociada.

El alcance final del proyecto son dos entregables locales:

- `dist/Tesis_Rodrigo_Rojas_con_datos.pdf`
- `dist/Presentacion_V1.pdf`

Los PDFs no se versionan ni se sincronizan con GitHub; se generan localmente desde los fuentes.

## Entrypoints

- `main_con_datos_privados.tex`: entrada final de la tesis con datos privados; carga `main.tex`.
- `main.tex`: cuerpo principal de la tesis. Mantiene portada, resumen, agradecimientos y el orden de capitulos.
- `tex/presentation/main.tex`: entrada final de la presentacion Beamer. Debe compilarse desde la raiz del repo.

## Motor y dependencias

- Motor: `pdflatex`.
- Orquestador recomendado: `latexmk`.
- Bibliografia: BibTeX con `apacite`; no usa `biber`.
- No requiere `shell-escape`.
- Scripts opcionales: `scripts/postprocess_resultado_perdida_svgs.py` requiere Inkscape y puede usar `TESIS_RESULTS_DIR` e `INKSCAPE_EXE` como variables de entorno.

## Estructura

- `tex/chapters/`: capitulos y secciones reales de la tesis.
- `tex/styles/`: template y configuracion del template.
- `tex/presentation/`: fuente LaTeX de la presentacion.
- `assets/figures/thesis/`: figuras usadas por la tesis.
- `assets/figures/presentation/`: figuras usadas por la presentacion.
- `assets/figures/template/`: logos usados por el template.
- `bibliography/`: `.bib` y estilos `.bst` usados.
- `scripts/`: herramientas reproducibles o auxiliares.
- `build/`: auxiliares y PDFs intermedios generados por `latexmk`.
- `dist/`: PDFs finales locales copiados para entrega; no versionados.
- `archive/`: archivos antiguos, duplicados, no usados o que requieren revision.
