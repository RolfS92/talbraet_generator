# Talbræt-generator

Lokal Streamlit-app til generering af 8x8 talbrætter med Dansk Skoleskak-layout, tabelvisning, validering og eksport.

## Kør lokalt

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Indhold

- Springerrute står øverst i preset-listen
- Kongerute-preset hvor du vælger tabellen i sidebaren og bruger fri kongerute
- Motiv-preset hvor kongeruten følger 8x8-formerne Springer eller Bonde
- Tabel-preset hvor du selv vælger tabellen i sidebaren
- Springerrute-preset hvor du vælger tabellen i sidebaren, start/slut og antal spring
- Eksport i både A4 og A3 liggende til PNG og PDF
- Liggende arkopsætning med titel øverst til venstre, logo øverst til højre og `skoleskak.dk` nederst til venstre
- Kvadratisk 8x8 bræt med 8-1 til venstre og A-H nederst i alle visninger og eksporter
- Tabelvisning i appen og eksport til JSON, PNG og PDF
- Eksport til JSON, PNG og PDF
