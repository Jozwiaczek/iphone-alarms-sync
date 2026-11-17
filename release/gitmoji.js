// semantic-release plugin: the gitmoji spec (gitmojis package) decides the bump,
// and the notes are written for users reading them in Home Assistant (HACS).
// CLI: `node release/gitmoji.js [tag]` prints the notes for commits since tag
// (default: the last stable tag).
const fs = require('fs');
const { execFileSync } = require('child_process');
const { gitmojis } = require('gitmojis');

const FE0F = /️/g;
const SPEC = new Map();
for (const g of gitmojis) {
  SPEC.set(g.emoji.replace(FE0F, ''), g);
  SPEC.set(g.code, g);
}
const RANK = { major: 3, minor: 2, patch: 1 };

function parse(subject, body = '') {
  const [first, ...rest] = subject.trim().split(/\s+/);
  const spec = SPEC.get(first.replace(FE0F, ''));
  let text = spec ? rest.join(' ') : subject.trim();
  const pr = text.match(/\s*\(#(\d+)\)$/);
  if (pr) text = text.slice(0, pr.index);
  const breaking = /^BREAKING[ -]CHANGE:/m.test(body);
  return {
    emoji: spec ? spec.emoji : '',
    semver: breaking ? 'major' : (spec && spec.semver) || null,
    text,
    pr: pr ? pr[1] : null,
  };
}

function releaseType(commits) {
  let best = null;
  for (const c of commits) {
    const { semver } = parse(c.subject, c.body);
    if (semver && (!best || RANK[semver] > RANK[best])) best = semver;
  }
  return best;
}

function repoUrl(url) {
  const m = url.match(/github\.com[:/](.+?)(?:\.git)?$/);
  return `https://github.com/${m[1]}`;
}

function line(c, repo) {
  const p = parse(c.subject, c.body);
  const ref = p.pr
    ? `[#${p.pr}](${repo}/pull/${p.pr})`
    : `[${c.hash.slice(0, 7)}](${repo}/commit/${c.hash})`;
  return `- ${p.emoji ? p.emoji + ' ' : ''}${p.text} (${ref})`;
}

function notes(commits, repo) {
  const groups = { major: [], minor: [], patch: [], other: [] };
  // semantic-release passes commits newest first; show them oldest first.
  for (const c of [...commits].reverse()) {
    groups[parse(c.subject, c.body).semver || 'other'].push(line(c, repo));
  }
  const out = [];
  const section = (title, lines) => lines.length && out.push(`### ${title}\n\n${lines.join('\n')}`);
  section('💥 Breaking changes', groups.major);
  section('✨ New features', groups.minor);
  section('🐛 Fixes and improvements', groups.patch);
  if (groups.other.length) {
    out.push(
      `<details>\n<summary>🧰 Under the hood (${groups.other.length})</summary>\n\n` +
        `${groups.other.join('\n')}\n\n</details>`,
    );
  }
  // HACS appends the next release's `# vX.Y.Z` right after this text: end with a blank line.
  return out.join('\n\n') + '\n\n';
}

// Plugin steps
const analyzeCommits = (_, { commits }) => releaseType(commits);

const generateNotes = (_, { commits, options }) => notes(commits, repoUrl(options.repositoryUrl));

function prepare(_, { cwd, lastRelease, nextRelease, options }) {
  const file = `${cwd}/CHANGELOG.md`;
  const repo = repoUrl(options.repositoryUrl);
  const date = new Date().toISOString().slice(0, 10);
  const title = lastRelease.gitTag
    ? `[${nextRelease.gitTag}](${repo}/compare/${lastRelease.gitTag}...${nextRelease.gitTag})`
    : nextRelease.gitTag;
  const old = fs.existsSync(file) ? fs.readFileSync(file, 'utf8').replace(/^# Changelog\s*/, '') : '';
  fs.writeFileSync(file, `# Changelog\n\n## ${title} (${date})\n\n${nextRelease.notes.trim()}\n\n${old}`.trimEnd() + '\n');
}

module.exports = { analyzeCommits, generateNotes, prepare, parse, releaseType, notes };

if (require.main === module) {
  const git = (...args) => execFileSync('git', args, { encoding: 'utf8' }).trim();
  const from = process.argv[2] || git('describe', '--tags', '--abbrev=0', '--exclude', '*-beta*');
  const commits = git('log', '--format=%H%x1f%s%x1f%b%x1e', `${from}..HEAD`)
    .split('\x1e')
    .map((r) => r.trim())
    .filter(Boolean)
    .map((r) => {
      const [hash, subject, body] = r.split('\x1f');
      return { hash, subject, body };
    });
  process.stdout.write(notes(commits, repoUrl(git('remote', 'get-url', 'origin'))));
}
