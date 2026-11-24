module.exports = {
  branches: ['main'],
  plugins: [
    // Version bump, release notes and CHANGELOG.md from gitmoji commits.
    './release/gitmoji.js',
    [
      '@semantic-release/exec',
      {
        // Runs in --dry-run too: the beta job reads the next version from this file.
        verifyReleaseCmd: 'echo ${nextRelease.version} > .next-version',
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
        message: ':bookmark: v${nextRelease.version} [skip ci]',
      },
    ],
    // No "included in version" comment on every released PR: it mails each one.
    ['@semantic-release/github', { successComment: false }],
  ],
};
