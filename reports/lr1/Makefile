# =====================================================================
# Сборка отчёта по лабораторной работе.
#   make lab            — собрать диаграммы и скомпилировать PDF
#   make lab-diagrams   — только пересобрать диаграммы PlantUML
#   make lab-pdf        — только пересобрать PDF (диаграммы не трогает)
#   make lab-clean      — удалить артефакты сборки
# =====================================================================

LAB_MAIN := lab/lab_report
LATEXMK  := latexmk -pdf -shell-escape -interaction=nonstopmode -halt-on-error

.PHONY: lab lab-diagrams lab-pdf lab-clean

lab: lab-diagrams lab-pdf

lab-diagrams:
	bash lab/diagrams/build.sh

lab-pdf:
	$(LATEXMK) $(LAB_MAIN).tex

lab-clean:
	latexmk -C $(LAB_MAIN).tex
	rm -rf _minted-lab_report
