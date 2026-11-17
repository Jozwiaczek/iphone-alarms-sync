const test = require('node:test');
const assert = require('node:assert/strict');
const { parse, releaseType, notes } = require('./gitmoji');

const repo = 'https://github.com/o/r';
const c = (subject, body = '', hash = 'abcdef1234567890') => ({ subject, body, hash });

test('parse reads the emoji in any form and moves the PR number out', () => {
  assert.deepEqual(parse('⬆️ Update segno (#28)'), { emoji: '⬆️', semver: 'patch', text: 'Update segno', pr: '28' });
  assert.equal(parse('⬆ Update segno').semver, 'patch');
  assert.equal(parse(':sparkles: Add it').emoji, '✨');
  assert.deepEqual(parse('Merge branch main'), { emoji: '', semver: null, text: 'Merge branch main', pr: null });
  assert.equal(parse('🐛 Fix it', 'BREAKING CHANGE: setup again').semver, 'major');
});

test('only user-facing gitmoji release', () => {
  assert.equal(releaseType([c('📝 Docs'), c('✅ Tests'), c('👷 Bump lodash')]), null);
  assert.equal(releaseType([c('📝 Docs'), c('💄 Look')]), 'patch');
  assert.equal(releaseType([c('🐛 Fix'), c('✨ New'), c('💄 Look')]), 'minor');
  assert.equal(releaseType([c('✨ New'), c('💥 Break')]), 'major');
});

test('notes have no version heading, fold internal changes and end with a blank line for HACS', () => {
  const out = notes([c('📝 Explain the README (#35)'), c('🐛 Fix "goes off" time'), c('✨ Add triggers (#37)')], repo);
  assert.equal(
    out,
    [
      '### ✨ New features',
      '',
      '- ✨ Add triggers ([#37](https://github.com/o/r/pull/37))',
      '',
      '### 🐛 Fixes and improvements',
      '',
      '- 🐛 Fix "goes off" time ([abcdef1](https://github.com/o/r/commit/abcdef1234567890))',
      '',
      '<details>',
      '<summary>🧰 Under the hood (1)</summary>',
      '',
      '- 📝 Explain the README ([#35](https://github.com/o/r/pull/35))',
      '',
      '</details>',
      '',
      '',
    ].join('\n'),
  );
});

test('prepare puts the new release on top and keeps the old ones', () => {
  const fs = require('fs');
  const os = require('os');
  const { prepare } = require('./gitmoji');
  const cwd = fs.mkdtempSync(`${os.tmpdir()}/changelog-`);
  fs.writeFileSync(`${cwd}/CHANGELOG.md`, '# Changelog\n\n## [v1.0.0](x) (2026-01-01)\n\n### ✨ New features\n\n- ✨ Old\n');
  prepare({}, {
    cwd,
    lastRelease: { gitTag: 'v1.0.0' },
    nextRelease: { gitTag: 'v1.1.0', notes: '### ✨ New features\n\n- ✨ New\n\n' },
    options: { repositoryUrl: 'git@github.com:o/r.git' },
  });
  const out = fs.readFileSync(`${cwd}/CHANGELOG.md`, 'utf8');
  assert.equal(out.match(/^# Changelog$/gm).length, 1);
  assert.match(out, /^# Changelog\n\n## \[v1\.1\.0\]\(https:\/\/github\.com\/o\/r\/compare\/v1\.0\.0\.\.\.v1\.1\.0\) \(\d{4}-\d\d-\d\d\)\n\n### ✨ New features\n\n- ✨ New\n\n## \[v1\.0\.0\]/);
  assert.ok(out.endsWith('- ✨ Old\n'));
});
