# Build the paper. Requires `tectonic` (brew install tectonic) and `uv`.
# Figures are generated from the raw run data before the PDF is compiled.

.PHONY: all figures clean

all: paper.pdf

figures:
	cd .. && uv run python analysis/make_figures.py

paper.pdf: paper.tex references.bib figures
	tectonic paper.tex

clean:
	rm -f paper.aux paper.log paper.out paper.bbl paper.blg paper.bcf \
	      paper.run.xml paper.fdb_latexmk paper.fls paper.synctex.gz
