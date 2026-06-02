# LATEX_TESIS

Proyecto LaTeX de la tesis **"Estudio de amenaza y vulnerabilidad sismica de Falla San Ramon"** y de la presentacion de defensa asociada.

El alcance final del repositorio son dos entregables:

- `dist/Tesis_Rodrigo_Rojas_con_datos.pdf`
- `dist/Presentacion_V1.pdf`

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

## Compilacion

Con `latexmk` desde la raiz:

```powershell
latexmk -pdf main_con_datos_privados.tex
latexmk -pdf -jobname=Presentacion_V1 tex/presentation/main.tex
```

`latexmkrc` manda la compilacion a `build/`. Para dejar los PDFs finales en `dist/`:

```powershell
New-Item -ItemType Directory -Force dist
Copy-Item build/main_con_datos_privados.pdf dist/Tesis_Rodrigo_Rojas_con_datos.pdf
Copy-Item build/Presentacion_V1.pdf dist/Presentacion_V1.pdf
```

Solo esos dos PDFs finales de `dist/` deben versionarse. Cualquier otra salida generada en `dist/` queda ignorada.

Si tienes `make` en un entorno POSIX/Git Bash:

```bash
make pdf
```

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
- `dist/`: PDFs finales copiados para entrega.
- `archive/`: archivos antiguos, duplicados, no usados o que requieren revision.

## Limpieza

```powershell
latexmk -c main_con_datos_privados.tex
latexmk -c -jobname=Presentacion_V1 tex/presentation/main.tex
```

Para una limpieza completa, elimina `build/` y `dist/` despues de cerrar visores PDF.

## Notas de archivo

Los activos usados estan en `assets/` y deben versionarse. Los PDFs historicos, auxiliares antiguos, figuras no referenciadas y variantes no finales se movieron a `archive/` sin borrado definitivo. Parte de ese archivo local queda ignorado por `.gitignore` para evitar subir salidas pesadas o no usadas a GitHub.
