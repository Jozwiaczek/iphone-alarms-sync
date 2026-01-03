# Testowanie procesu release

## Metoda 1: Dry-run semantic-release (zalecane)

Uruchom semantic-release w trybie testowym, aby zobaczyć co by się stało bez faktycznego publikowania:

```bash
# Upewnij się, że masz zainstalowane zależności
npm install

# Uruchom dry-run
npx semantic-release --dry-run
```

To pokaże:
- Jaką wersję by utworzył
- Jakie commity by przeanalizował
- Jakie pliki by zaktualizował
- Jakie release by opublikował

**Uwaga:** Dry-run może wymagać dostępu do GitHub API, więc może być potrzebny `GITHUB_TOKEN`.

## Metoda 2: Test poszczególnych komponentów

### Test aktualizacji manifest.json

```bash
# Symuluj aktualizację wersji
jq --arg v "1.0.3" '.version = $v' custom_components/iphone_alarms_sync/manifest.json > tmp.json && mv tmp.json custom_components/iphone_alarms_sync/manifest.json

# Sprawdź wynik
cat custom_components/iphone_alarms_sync/manifest.json | grep version
```

### Test generowania changelogu

```bash
# Uruchom gitmoji-changelog (jeśli jest dostępny)
npx gitmoji-changelog

# Lub sprawdź czy CHANGELOG.md został zaktualizowany
git diff CHANGELOG.md
```

### Test tworzenia ZIP

```bash
# Utwórz ZIP
cd custom_components && zip -r ../iphone-alarms-sync.zip iphone_alarms_sync

# Sprawdź czy zawiera aktualną wersję
unzip -l iphone-alarms-sync.zip | grep manifest.json
unzip -p iphone-alarms-sync.zip iphone_alarms_sync/manifest.json | grep version
```

## Metoda 3: Test na branchu testowym

1. Utwórz branch testowy:
```bash
git checkout -b test-release
```

2. Dodaj testowy commit z gitmoji:
```bash
echo "test" > test.txt
git add test.txt
git commit -m "🐛 Test release process"
```

3. Uruchom semantic-release (możesz użyć dry-run):
```bash
npx semantic-release --dry-run
```

4. Sprawdź co by się zmieniło:
```bash
git status
git diff
```

5. Usuń branch po teście:
```bash
git checkout main
git branch -D test-release
```

## Metoda 4: Test w GitHub Actions (najpewniejsze)

1. Utwórz branch testowy i push:
```bash
git checkout -b test-release-workflow
git push origin test-release-workflow
```

2. Dodaj testowy commit:
```bash
echo "test" > test.txt
git add test.txt
git commit -m "🐛 Test release workflow"
git push
```

3. Sprawdź workflow w GitHub Actions:
   - Przejdź do: https://github.com/Jozwiaczek/iphone-alarms-sync/actions
   - Znajdź uruchomiony workflow
   - Sprawdź logi każdego kroku

4. Jeśli wszystko działa, możesz zrobić merge do main:
```bash
git checkout main
git merge test-release-workflow
git push
```

## Weryfikacja po release

Po faktycznym release sprawdź:

1. **GitHub Release:**
   - https://github.com/Jozwiaczek/iphone-alarms-sync/releases
   - Czy nowa wersja została utworzona
   - Czy ZIP został załączony
   - Czy release notes są poprawne

2. **CHANGELOG.md:**
   - Czy został zaktualizowany
   - Czy zawiera nowe commity
   - Czy format jest poprawny

3. **manifest.json:**
   - Czy wersja została zaktualizowana
   - Czy zmiana została zcommitowana

4. **Git tags:**
   ```bash
   git fetch --tags
   git tag -l
   ```

## Rozwiązywanie problemów

### Problem: gitmoji-changelog nie działa

Jeśli `npx gitmoji-changelog` nie działa, możesz:
1. Sprawdzić czy pakiet istnieje: `npm view gitmoji-changelog`
2. Użyć alternatywnego narzędzia lub wrócić do gitmoji-changelog-action
3. Sprawdzić dokumentację: https://github.com/sercanuste/gitmoji-changelog-action

### Problem: Dry-run wymaga GITHUB_TOKEN

```bash
export GITHUB_TOKEN=your_token_here
npx semantic-release --dry-run
```

### Problem: ZIP nie zawiera aktualnej wersji

Upewnij się, że ZIP jest tworzony PO aktualizacji manifest.json w `.releaserc.js`.

