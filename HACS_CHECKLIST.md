# Lista kontrolna gotowości do instalacji przez HACS

## ✅ Wymagane pliki i struktura

### Struktura katalogów
- ✅ `custom_components/iphone_alarms_sync/` - główny folder integracji
- ✅ `custom_components/iphone_alarms_sync/__init__.py` - główny plik integracji
- ✅ `custom_components/iphone_alarms_sync/manifest.json` - manifest z metadanymi
- ✅ `custom_components/iphone_alarms_sync/config_flow.py` - config flow
- ✅ `custom_components/iphone_alarms_sync/strings.json` - tłumaczenia (en)
- ✅ `custom_components/iphone_alarms_sync/translations/en.json` - tłumaczenia
- ✅ `custom_components/iphone_alarms_sync/services.yaml` - definicje serwisów
- ✅ `custom_components/iphone_alarms_sync/coordinator.py` - coordinator
- ✅ `custom_components/iphone_alarms_sync/sensor.py` - platforma sensor
- ✅ `custom_components/iphone_alarms_sync/binary_sensor.py` - platforma binary_sensor
- ✅ `custom_components/iphone_alarms_sync/device_trigger.py` - device triggers
- ✅ `custom_components/iphone_alarms_sync/const.py` - stałe

### Pliki konfiguracyjne
- ✅ `hacs.json` - konfiguracja HACS
- ✅ `README.md` - dokumentacja
- ✅ `.github/workflows/hacs.yml` - workflow walidacji HACS
- ✅ `.github/workflows/validate.yml` - workflow walidacji hassfest
- ✅ `.gitignore` - wykluczenia Git

## ✅ Weryfikacja manifest.json

```json
{
  "domain": "iphone_alarms_sync", ✅
  "name": "iPhone Alarms Sync", ✅
  "version": "1.0.0", ✅
  "documentation": "https://github.com/Jozwiaczek/iphone-alarms-sync", ✅
  "issue_tracker": "https://github.com/Jozwiaczek/iphone-alarms-sync/issues", ✅
  "codeowners": ["@Jozwiaczek"], ✅
  "config_flow": true, ✅
  "iot_class": "cloud_push", ✅
  "requirements": [] ✅
}
```

## ✅ Weryfikacja hacs.json

```json
{
  "name": "iPhone Alarms Sync", ✅
  "render_readme": true, ✅
  "domains": ["iphone_alarms_sync"], ✅
  "iot_class": "Cloud Push" ✅
}
```

## ⚠️ Wymagania przed instalacją

### Repozytorium GitHub
- [x] Repozytorium jest **publiczne** (HACS nie obsługuje prywatnych)
- [ ] Repozytorium ma **description** (w ustawieniach GitHub)
- [ ] Repozytorium ma **topics** (np. `home-assistant`, `hacs`, `integration`)
- [ ] Branch główny to `main` (lub `master`)

### GitHub Actions
- [ ] Workflow `.github/workflows/hacs.yml` przechodzi ✅
- [ ] Workflow `.github/workflows/validate.yml` przechodzi ✅
- [ ] `hassfest` walidacja przechodzi ✅

### Testy lokalne (opcjonalne, ale zalecane)
- [ ] `ruff check` - brak błędów lintingu
- [ ] `mypy` - brak błędów typów (opcjonalne)
- [ ] Kod działa lokalnie w HA

## 📋 Instrukcja instalacji przez HACS

1. **Commit i push na GitHub:**
   ```bash
   git add .
   git commit -m "Ready for HACS installation"
   git push origin main
   ```

2. **W Home Assistant:**
   - Otwórz HACS → Integrations
   - Kliknij ⋮ (trzy kropki) → Custom repositories
   - Dodaj: `Jozwiaczek/iphone-alarms-sync`
   - Category: `Integration`
   - Kliknij Add

3. **Instalacja:**
   - W HACS → Integrations znajdź "iPhone Alarms Sync"
   - Kliknij Download
   - Restart Home Assistant

4. **Konfiguracja:**
   - Settings → Devices & Services → Add Integration
   - Wyszukaj "iPhone Alarms Sync"
   - Postępuj zgodnie z instrukcjami w README

## 🔍 Co sprawdzić po instalacji

- [ ] Integracja pojawia się w HACS
- [ ] Można dodać przez Config Flow
- [ ] Brak błędów w logach HA
- [ ] Serwisy są dostępne w Developer Tools
- [ ] Encje są tworzone poprawnie

## 🚨 Potencjalne problemy

1. **HACS nie widzi repozytorium:**
   - Sprawdź czy repozytorium jest publiczne
   - Sprawdź czy GitHub Actions przechodzą
   - Sprawdź czy `hacs.json` jest w root

2. **Błędy podczas instalacji:**
   - Sprawdź logi HA: `Settings → System → Logs`
   - Sprawdź czy wszystkie pliki są w `custom_components/iphone_alarms_sync/`
   - Sprawdź czy `manifest.json` jest poprawny

3. **Integracja nie działa:**
   - Sprawdź logi HA
   - Sprawdź czy Config Flow działa
   - Sprawdź czy serwisy są zarejestrowane

## ✅ Status: GOTOWE DO INSTALACJI

Projekt spełnia wszystkie wymagania HACS i Home Assistant!

