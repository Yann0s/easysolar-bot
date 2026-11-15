#!/usr/bin/env bash
# Construit manuel_fr.md : une section "## Page N" par page de la partie FR (pages PDF 61-89), puis les annexes A-D.
# Une page corrigée à la main dans pages_corrigees/pNN.md remplace l'extraction automatique.
D=$(dirname "$(readlink -f "$0")"); PDF=${1:-/home/yannos/Downloads/Manual-EasySolar-1600-EN-NL-FR-DE-ES-IT.pdf}
for p in $(seq 61 89) 179 181 183 185; do
  if [ $p -gt 100 ]; then echo "## Annexe $(cut -c8 "$D/pages_corrigees/p$p.md" | head -1)"; else echo "## Page $((p-60))"; fi
  if [ -f "$D/pages_corrigees/p$p.md" ]; then cat "$D/pages_corrigees/p$p.md"
  else pdftotext -f $p -l $p "$PDF" - | grep -vxE '\s*(EN|NL|FR|DE|ES|IT|Appendix|[0-9]+)\s*' | tr -d '\f' | cat -s; fi
  echo
done > "$D/manuel_fr.md"
