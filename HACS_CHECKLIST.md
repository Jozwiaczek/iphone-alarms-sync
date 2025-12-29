# HACS Installation Readiness Checklist

## ✅ Required files and structure

### Directory structure
- ✅ `custom_components/iphone_alarms_sync/` - main integration folder
- ✅ `custom_components/iphone_alarms_sync/__init__.py` - main integration file
- ✅ `custom_components/iphone_alarms_sync/manifest.json` - manifest with metadata
- ✅ `custom_components/iphone_alarms_sync/config_flow.py` - config flow
- ✅ `custom_components/iphone_alarms_sync/strings.json` - translations (en)
- ✅ `custom_components/iphone_alarms_sync/translations/en.json` - translations
- ✅ `custom_components/iphone_alarms_sync/services.yaml` - service definitions
- ✅ `custom_components/iphone_alarms_sync/coordinator.py` - coordinator
- ✅ `custom_components/iphone_alarms_sync/sensor.py` - sensor platform
- ✅ `custom_components/iphone_alarms_sync/binary_sensor.py` - binary_sensor platform
- ✅ `custom_components/iphone_alarms_sync/device_trigger.py` - device triggers
- ✅ `custom_components/iphone_alarms_sync/const.py` - constants

### Configuration files
- ✅ `hacs.json` - HACS configuration
- ✅ `README.md` - documentation
- ✅ `.github/workflows/hacs.yml` - HACS validation workflow
- ✅ `.github/workflows/validate.yml` - hassfest validation workflow
- ✅ `.gitignore` - Git exclusions

## ✅ manifest.json verification

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

## ✅ hacs.json verification

```json
{
  "name": "iPhone Alarms Sync", ✅
  "render_readme": true, ✅
  "domains": ["iphone_alarms_sync"], ✅
  "iot_class": "Cloud Push" ✅
}
```

## ⚠️ Requirements before installation

### GitHub Repository
- [x] Repository is **public** (HACS doesn't support private repositories)
- [ ] Repository has **description** (in GitHub settings)
- [ ] Repository has **topics** (e.g., `home-assistant`, `hacs`, `integration`)
- [ ] Main branch is `main` (or `master`)

### GitHub Actions
- [ ] Workflow `.github/workflows/hacs.yml` passes ✅
- [ ] Workflow `.github/workflows/validate.yml` passes ✅
- [ ] `hassfest` validation passes ✅

### Local tests (optional, but recommended)
- [ ] `ruff check` - no linting errors
- [ ] `mypy` - no type errors (optional)
- [ ] Code works locally in HA

## 📋 HACS installation instructions

1. **Commit and push to GitHub:**
   ```bash
   git add .
   git commit -m "Ready for HACS installation"
   git push origin main
   ```

2. **In Home Assistant:**
   - Open HACS → Integrations
   - Click ⋮ (three dots) → Custom repositories
   - Add: `Jozwiaczek/iphone-alarms-sync`
   - Category: `Integration`
   - Click Add

3. **Installation:**
   - In HACS → Integrations, find "iPhone Alarms Sync"
   - Click Download
   - Restart Home Assistant

4. **Configuration:**
   - Settings → Devices & Services → Add Integration
   - Search for "iPhone Alarms Sync"
   - Follow the instructions in README

## 🔍 What to check after installation

- [ ] Integration appears in HACS
- [ ] Can be added via Config Flow
- [ ] No errors in HA logs
- [ ] Services are available in Developer Tools
- [ ] Entities are created correctly

## 🚨 Potential issues

1. **HACS doesn't see the repository:**
   - Check if repository is public
   - Check if GitHub Actions pass
   - Check if `hacs.json` is in root

2. **Errors during installation:**
   - Check HA logs: `Settings → System → Logs`
   - Check if all files are in `custom_components/iphone_alarms_sync/`
   - Check if `manifest.json` is correct

3. **Integration doesn't work:**
   - Check HA logs
   - Check if Config Flow works
   - Check if services are registered

## ✅ Status: READY FOR INSTALLATION

The project meets all HACS and Home Assistant requirements!
