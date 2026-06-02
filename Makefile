LATEXMK ?= latexmk

PRIVATE_MAIN := main_con_datos_privados
PRESENTATION_MAIN := tex/presentation/main
PRESENTATION_JOB := Presentacion_V1

DIST_PRIVATE := dist/Tesis_Rodrigo_Rojas_con_datos.pdf
DIST_PRESENTATION := dist/Presentacion_V1.pdf

.PHONY: all pdf thesis private presentation clean distclean watch

all: pdf

pdf: thesis presentation

thesis:
	$(LATEXMK) -pdf $(PRIVATE_MAIN).tex
	mkdir -p dist
	cp build/$(PRIVATE_MAIN).pdf $(DIST_PRIVATE)

private: thesis

presentation:
	$(LATEXMK) -pdf -jobname=$(PRESENTATION_JOB) $(PRESENTATION_MAIN).tex
	mkdir -p dist
	cp build/$(PRESENTATION_JOB).pdf $(DIST_PRESENTATION)

watch:
	$(LATEXMK) -pdf -pvc $(PRIVATE_MAIN).tex

clean:
	$(LATEXMK) -c $(PRIVATE_MAIN).tex
	$(LATEXMK) -c -jobname=$(PRESENTATION_JOB) $(PRESENTATION_MAIN).tex

distclean:
	$(LATEXMK) -C $(PRIVATE_MAIN).tex
	$(LATEXMK) -C -jobname=$(PRESENTATION_JOB) $(PRESENTATION_MAIN).tex
	rm -rf build dist
