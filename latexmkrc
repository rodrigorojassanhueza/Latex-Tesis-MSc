$pdf_mode = 1;
$out_dir = 'build';
$max_repeat = 5;

$pdflatex = 'pdflatex -interaction=nonstopmode -file-line-error -halt-on-error -recorder -synctex=0 %O %S';
$bibtex = 'bibtex %O %B';

$clean_ext = 'bbl blg lof lot nav out run.xml snm toc vrb synctex.gz';
$cleanup_includes_cusdep_generated = 1;
