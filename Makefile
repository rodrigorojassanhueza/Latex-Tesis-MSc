LATEXMK ?= latexmk

PRIVATE_MAIN := main_con_datos_privados
PRESENTATION_MAIN := tex/presentation/main
PRESENTATION_JOB := Presentación

DIST_PRIVATE := dist/Tesis_Rodrigo_Rojas_con_datos.pdf
DIST_PRESENTATION := dist/Presentación.pdf

.PHONY: all pdf thesis private presentation clean distclean watch

all: pdf

pdf: thesis presentation

thesis:
	$(LATEXMK) -pdf $(PRIVATE_MAIN).tex
	mkdir -p dist
	cp build/$(PRIVATE_MAIN).pdf $(DIST_PRIVATE)

private: thesis

presentation:
	mkdir -p dist
	rm -f dist/Presentacion_V1*.pdf dist/presentacion.pdf dist/presentation*.pdf build/Presentacion_V1.pdf build/presentacion.pdf build/Presentación.pdf
	$(LATEXMK) -pdf -outdir=dist -jobname="$(PRESENTATION_JOB)" $(PRESENTATION_MAIN).tex
	rm -f "dist/$(PRESENTATION_JOB).aux" "dist/$(PRESENTATION_JOB).bbl" "dist/$(PRESENTATION_JOB).blg" "dist/$(PRESENTATION_JOB).fdb_latexmk" "dist/$(PRESENTATION_JOB).fls" "dist/$(PRESENTATION_JOB).log" "dist/$(PRESENTATION_JOB).nav" "dist/$(PRESENTATION_JOB).out" "dist/$(PRESENTATION_JOB).snm" "dist/$(PRESENTATION_JOB).toc"

watch:
	$(LATEXMK) -pdf -pvc $(PRIVATE_MAIN).tex

clean:
	$(LATEXMK) -c $(PRIVATE_MAIN).tex
	rm -f "dist/$(PRESENTATION_JOB).aux" "dist/$(PRESENTATION_JOB).bbl" "dist/$(PRESENTATION_JOB).blg" "dist/$(PRESENTATION_JOB).fdb_latexmk" "dist/$(PRESENTATION_JOB).fls" "dist/$(PRESENTATION_JOB).log" "dist/$(PRESENTATION_JOB).nav" "dist/$(PRESENTATION_JOB).out" "dist/$(PRESENTATION_JOB).snm" "dist/$(PRESENTATION_JOB).toc"

distclean:
	$(LATEXMK) -C $(PRIVATE_MAIN).tex
	$(LATEXMK) -C -outdir=dist -jobname="$(PRESENTATION_JOB)" $(PRESENTATION_MAIN).tex
	rm -rf build dist
