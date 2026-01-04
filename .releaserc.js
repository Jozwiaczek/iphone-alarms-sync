const path = require('path');
const fs = require('fs');

const templateFile = path.resolve(__dirname, 'templates/release-notes.hbs');
const commitTemplateFile = path.resolve(__dirname, 'templates/commit.hbs');

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
            ':arrow_up:',
            ':arrow_down:',
            ':pushpin:',
            ':chart_with_upwards_trend:',
            ':heavy_plus_sign:',
            ':heavy_minus_sign:',
            ':wrench:',
            ':globe_with_meridians:',
            ':rewind:',
            ':package:',
            ':children_crossing:',
            ':iphone:',
            ':egg:',
            ':alembic:',
            ':mag:',
            ':label:',
            ':triangular_flag_on_post:',
            ':goal_net:',
            ':dizzy:',
            ':wastebasket:',
            ':passport_control:',
            ':adhesive_bandage:',
            ':necktie:',
            ':t-rex:',
            ':art:',
            ':memo:',
            ':truck:',
            ':building_construction:',
            ':fire:',
            ':green_heart:',
            ':rotating_light:',
            ':recycle:',
            ':white_check_mark:',
            ':test_tube:',
            ':rocket:',
            ':alien:',
            ':bento:',
            ':clown_face:',
            ':see_no_evil:',
            ':camera_flash:',
            ':wheelchair:',
            ':bulb:',
            ':beers:',
            ':speech_balloon:',
            ':card_file_box:',
            ':loud_sound:',
            ':mute:',
            ':busts_in_silhouette:',
            ':closed_lock_with_key:',
            ':bookmark:',
            ':construction:',
            ':hammer:',
            ':poop:',
            ':twisted_rightwards_arrows:',
            ':seedling:',
            ':monocle_face:',
            ':coffin:',
            ':stethoscope:',
            ':bricks:',
            ':technologist:',
            ':money_with_wings:',
            ':thread:',
            ':safety_vest:',
            ':airplane:',
          ],
        },
        releaseNotes: {
          template: fs.readFileSync(templateFile, 'utf-8'),
          partials: {
            commitTemplate: fs.readFileSync(commitTemplateFile, 'utf-8'),
          },
          issueResolution: {
            template: '{baseUrl}/{owner}/{repo}/issues/{ref}',
            baseUrl: 'https://github.com',
            source: 'github.com',
            removeFromCommit: false,
            regex: /#\d+/g,
          },
        },
      },
    ],
    [
      '@semantic-release/changelog',
      {
        changelogFile: 'CHANGELOG.md',
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
      '@semantic-release/exec',
      {
        prepareCmd:
          'cd custom_components && zip -r ../iphone-alarms-sync.zip iphone_alarms_sync',
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

