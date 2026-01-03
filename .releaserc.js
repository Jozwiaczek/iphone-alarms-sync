module.exports = {
  branches: ['main'],
  plugins: [
    [
      'semantic-release-gitmoji',
      {
        releaseRules: {
          major: [':boom:'],
          minor: [':sparkles:', ':tada:', ':construction_worker:'],
          patch: [
            ':bug:',
            ':ambulance:',
            ':lock:',
            ':pencil2:',
            ':lipstick:',
            ':zap:',
            ':recycle:',
            ':wrench:',
            ':adhesive_bandage:',
            ':fire:',
            ':art:',
            ':truck:',
            ':building_construction:',
            ':memo:',
            ':green_heart:',
            ':rotating_light:',
            ':label:',
            ':heavy_plus_sign:',
            ':heavy_minus_sign:',
            ':wastebasket:',
          ],
        },
      },
    ],
    [
      '@semantic-release/changelog',
      {
        changelogFile: 'CHANGELOG.md',
        changelogTitle: '# Changelog\n\n',
      },
    ],
    [
      '@semantic-release/exec',
      {
        prepareCmd:
          'jq --arg v "${nextRelease.version}" \'.version = $v\' custom_components/iphone_alarms_sync/manifest.json > tmp.json && mv tmp.json custom_components/iphone_alarms_sync/manifest.json',
      },
    ],
    [
      '@semantic-release/git',
      {
        assets: [
          'CHANGELOG.md',
          'custom_components/iphone_alarms_sync/manifest.json',
        ],
        message: 'chore(release): ${nextRelease.version} [skip ci]',
      },
    ],
    [
      '@semantic-release/github',
      {
        assets: [
          { path: 'iphone-alarms-sync.zip', label: 'iphone-alarms-sync.zip' },
        ],
      },
    ],
  ],
};

