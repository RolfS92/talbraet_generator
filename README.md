# Talbræt-generator

Lokal Streamlit-app til generering af 8x8 talbrætter med Dansk Skoleskak-layout, tabelvisning, validering og eksport.

## Divisor-skak

Vælg **Divisor-skak** i preset-listen. Vælg divisor (fx 2 eller 4), talinterval og antal felter, der giver ekstra træk, og tryk **Generer nyt bræt**. Tallene fordeles tilfældigt, og tal må gentages. En brik får et ekstra træk, når den lander på et tal, som divisoren går op i uden rest.

**Vis felter med ekstra træk** viser facit og tager markeringerne med på printet. Lad feltet være slået fra til elevernes spillebræt. Reglen følger med i PNG- og PDF-eksport.

**Brug eksempelbrættet** genskaber de præcise 64 tal fra divisor-skak-eksemplet. Det har 38 felter delelige med 2 og 21 felter delelige med 4. Den valgte divisor bruges også på eksemplet.

## Opret et præcist bræt fra et billede

1. Vælg **Importér billede** under **Opret bræt**.
2. Upload PNG, JPG eller WebP (højst 10 MB og 20 megapixels). Brug et tydeligt, retvendt billede taget lige ovenfra.
3. Drej om nødvendigt billedet. Appen foreslår en beskæring, når den kan genkende et regelmæssigt bræt. Afgræns kun de 64 felter med kantvælgerne, uden ramme, koordinater eller øvrig tekst. Kontrollér, at de røde hjælpelinjer følger feltkanterne.
4. Tryk **Aflæs tal fra billedet**. Aflæsningen sker lokalt i appens serverproces med RapidOCR; der bruges ingen ekstern AI-tjeneste eller API-nøgle. Første aflæsning kan tage lidt tid.
5. Sammenlign alle 64 tal med billedet, og ret tabellen. Usikre eller manglende felter bliver fremhævet i en liste. Række 8 er øverst, og A–H går fra venstre mod højre. Markér, at tallene er kontrolleret, og tryk **Brug talbrættet**.
6. Vælg titel, farvetema og A4/A3, og download JSON, PNG eller PDF som for andre brætter.

Aflæsning kan fejle på skæve, slørede eller dækkede tal; den ændrer aldrig et manglende tal til 0 eller flytter de efterfølgende felter. Alle felter skal indeholde heltal fra -9999 til 9999, før brættet kan godkendes. **Udfyld tallene manuelt** kan også bruges, hvis billedaflæsningen ikke er tilgængelig. Nye rettelser skal godkendes med **Brug talbrættet** igen. Et nyt billede eller en ændret beskæring kræver en ny godkendelse.

## Kør lokalt

Python 3.12 anbefales. OCR-modellerne følger med den installerede pakke, så billeder ikke sendes videre til en tredjepart.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

På Linux skal OpenCV kunne finde `libgl1` og `libglib2.0-0`; `packages.txt` angiver systempakker til Streamlit Community Cloud. På egen Debian/Ubuntu-server installeres de med `sudo apt-get install libgl1 libglib2.0-0`. Installér også `fonts-dejavu-core`, hvis serveren ikke allerede har en TrueType-skrifttype til eksport.

Ved opdatering af en eksisterende installation skal de nye Python-afhængigheder installeres med `pip install -r requirements.txt`, og Streamlit-processen genstartes. En deployment, der kun henter Python-filer uden at opdatere afhængigheder, kan stadig bruge de øvrige brætter og manuel import, men ikke automatisk billedaflæsning.

## Test

```powershell
python -m unittest discover -s tests -v
```

GitHub Actions kontrollerer talregler, alle presets, importvalidering, placeringen af OCR-resultater, brugerfladens tilstand og printformater. OCR er altid et udkast til manuel kontrol, også når motoren rapporterer høj sikkerhed.

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
