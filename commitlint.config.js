module.exports = {
  extends: ['gitmoji'],
  parserPreset: {
    parserOpts: {
      headerPattern: /^(\p{Emoji}+)\s(.+)$/u,
      headerCorrespondence: ['type', 'subject'],
    },
  },
  rules: {
    'header-max-length': [2, 'always', 72],
    'type-empty': [0],
    'subject-empty': [0],
    'type-enum': [0],
  },
};

