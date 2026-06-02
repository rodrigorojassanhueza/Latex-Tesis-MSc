# PROJECT_MANIFEST

## Diagnostico inicial

- Rama de trabajo: `reorganize-latex-project`.
- Estado inicial: arbol Git limpio antes de mover archivos.
- Entregables finales del repositorio: tesis con datos privados y presentacion.
- Entrada final de tesis: `main_con_datos_privados.tex`, que carga `main.tex`.
- `main.tex`: cuerpo principal de tesis.
- Documento principal de presentacion: `presentacion_defensa/main.tex` antes de reorganizar.
- Motor detectado: `pdflatex` mediante `latexmk`; bibliografia con BibTeX y `apacite`.
- Compilacion inicial exitosa:
  - `main_con_datos_privados.tex`: 128 paginas, 69,126,044 bytes.
  - `main_sin_datos_privados.tex`: 128 paginas, 69,124,922 bytes; compilada solo como auditoria previa y archivada despues por quedar fuera del alcance final.
  - `presentacion_defensa/main.tex`: 32 paginas, 21,217,184 bytes.

## Estructura final

```text
.
|-- main.tex
|-- main_con_datos_privados.tex
|-- Makefile
|-- latexmkrc
|-- README.md
|-- PROJECT_MANIFEST.md
|-- tex/
|   |-- chapters/
|   |-- styles/
|   `-- presentation/
|-- assets/
|   `-- figures/
|       |-- thesis/
|       |-- presentation/
|       `-- template/
|-- bibliography/
|-- scripts/
|-- build/
|-- dist/
`-- archive/
    |-- unused/
    |-- old-versions/
    `-- review-needed/
```

## Grafo principal

```text
main_con_datos_privados.tex -> main.tex
main.tex -> tex/styles/template.tex -> tex/styles/template_config.tex
main.tex -> tex/chapters/cap1_introduccion.tex
main.tex -> tex/chapters/cap2_marco_teorico.tex
main.tex -> tex/chapters/cap3_contexto_geologico.tex
main.tex -> tex/chapters/cap4_metodologia.tex
main.tex -> tex/chapters/cap5_resultados.tex
main.tex -> tex/chapters/cap7_discusion.tex
main.tex -> tex/chapters/cap10_referencias.tex -> bibliography/library.bib

tex/presentation/main.tex -> assets/figures/presentation/fig_4_3_arbol_logico_tikz.tex
tex/presentation/main.tex -> tex/presentation/references_nocite.tex
tex/presentation/main.tex -> bibliography/library.bib
```

## Archivos usados

| Categoria | Ruta final | Comentario |
|---|---|---|
| Tesis final | `main_con_datos_privados.tex`, `main.tex` | Entrada final con datos privados y cuerpo principal desde la raiz. |
| Capitulos | `tex/chapters/*.tex` | Capitulos incluidos directa o indirectamente desde `main.tex`. |
| Template | `tex/styles/template*.tex` | Preambulo y configuracion local. |
| Bibliografia | `bibliography/library.bib` | Base usada por tesis y presentacion. |
| BST tesis | `bibliography/apacite_noinitials.bst` | Estilo usado por la tesis. |
| BST presentacion | `bibliography/presentation_apacite_noinitials.bst` | Se conserva separado porque no tiene el mismo hash que el de tesis. |
| Figuras tesis | `assets/figures/thesis/` | 106 archivos: 102 usados desde `figuras_tesis/` y 4 mapas copiados desde rutas externas. |
| Figuras presentacion | `assets/figures/presentation/` | 24 archivos usados por Beamer. |
| Logo template | `assets/figures/template/departamentos/uchile2.pdf` | Usado por portada de tesis y presentacion. |
| Scripts | `scripts/*.py` | Herramientas auxiliares; no son requeridas para compilar. |

## Archivados o dudosos

| Ruta | Motivo |
|---|---|
| `archive/unused/example.tex` | Ejemplo comentado; no participa en el grafo. |
| `archive/unused/main_sin_datos_privados.tex` | Variante sin datos privados; no es entregable final del repositorio. |
| `archive/old-versions/pdf/Tesis_Rodrigo_Rojas_sin_datos_no_final.pdf` | PDF generado de la variante sin datos; conservado como historico no-final. |
| `archive/review-needed/Anexos.tex` | No estaba incluido por `main.tex`; requiere decision editorial antes de reintegrarlo. |
| `archive/review-needed/natnumurl.bst` | BST no usado por la configuracion actual. |
| `archive/unused/presentation/references_duplicate.bib` | Duplicado exacto de `bibliography/library.bib`. |
| `archive/unused/presentation/figures/` | Figuras de presentacion no usadas por la compilacion real. |
| `archive/review-needed/graph_generation_work/` | Trabajo intermedio de generacion de graficos, no requerido para compilar. |
| `archive/old-versions/` | PDFs historicos, correcciones externas y auxiliares antiguos. |
| `archive/unused/figuras_tesis/` | Figuras no referenciadas por la tesis compilada; conservadas localmente e ignoradas para GitHub. |
| `archive/unused/img/` | Imagenes de template no usadas por el documento final. |

## Decisiones

- `main.tex` se mantuvo en la raiz por compatibilidad con Overleaf y flujos LaTeX estandar.
- Se eliminaron las 4 rutas absolutas hacia `Modelos_v2025` copiando los PDFs necesarios a `assets/figures/thesis/resultados_perdida/risk_maps/`.
- Se corrigio la ruta de `vulnerabilidad_junemann_paper.png` para que compile en sistemas sensibles a mayusculas/minusculas.
- `latexmkrc` usa `build/` como `out_dir`; los PDFs finales se copian a `dist/` para evitar opciones no portables de separacion de aux/PDF.
- `.gitignore` permite versionar solo `dist/Tesis_Rodrigo_Rojas_con_datos.pdf` y `dist/Presentacion_V1.pdf`; cualquier otra salida en `dist/` queda ignorada.
- Los assets usados dejaron de estar ignorados; los archivos historicos o no usados de gran tamano siguen archivados localmente e ignorados.

## Verificacion ejecutada

```powershell
latexmk -gg -pdf -interaction=nonstopmode -file-line-error -halt-on-error .\main_con_datos_privados.tex
latexmk -gg -pdf -interaction=nonstopmode -file-line-error -halt-on-error -jobname=Presentacion_V1 .\tex\presentation\main.tex
Copy-Item build/main_con_datos_privados.pdf dist/Tesis_Rodrigo_Rojas_con_datos.pdf
Copy-Item build/Presentacion_V1.pdf dist/Presentacion_V1.pdf
```

Resultado final:

| PDF | Paginas | Bytes |
|---|---:|---:|
| `dist/Tesis_Rodrigo_Rojas_con_datos.pdf` | 128 | 69,126,503 |
| `dist/Presentacion_V1.pdf` | 32 | 21,217,554 |

No quedaron auxiliares LaTeX sueltos en la raiz. No quedaron referencias a `figuras_tesis/`, `presentacion_defensa/`, `img/` ni rutas absolutas `G:/.../Modelos_v2025` en los `.tex` o `.fls` verificados.

## Warnings relevantes

- Tesis: advertencias `pdfTeX` de `PDF inclusion: multiple pdfs with page group included in a single page` en algunas figuras PDF combinadas.
- Presentacion: las mismas advertencias `pdfTeX` en dos figuras PDF y cinco `Underfull \hbox` en `assets/figures/presentation/fig_4_3_arbol_logico_tikz.tex`.
- BibTeX: `warning$ -- 0` en tesis privada y presentacion.
