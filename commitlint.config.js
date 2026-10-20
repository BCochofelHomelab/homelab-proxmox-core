module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // ✅ Type must be one of these, lowercase: errors, since the release
    // reads only lowercase fix/feat and anything else skips it silently
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'style', 'refactor', 'perf',
      'test', 'build', 'ci', 'chore', 'revert'
    ]],

    // ✅ Scope is optional and unrestricted
    'scope-empty': [1, 'always'],
    'scope-enum': [0, 'always'],

    // ✅ Subject must not be empty
    'subject-empty': [2, 'never'],

    // ✅ Subject casing is relaxed
    'subject-case': [1, 'always', ['sentence-case', 'lower-case', 'start-case']],

    // ✅ Trailing punctuation allowed
    'subject-full-stop': [0, 'never'],

    // ✅ Length limits are relaxed
    'header-max-length': [1, 'always', 120],
    'subject-max-length': [1, 'always', 100],
    'body-max-line-length': [1, 'always', 120],
    'footer-max-line-length': [1, 'always', 120],

    // ✅ Blank lines before body/footer encouraged
    'body-leading-blank': [1, 'always'],
    'footer-leading-blank': [1, 'always'],

    // ✅ Type must be lowercase (`Fix:` releases nothing)
    'type-case': [2, 'always', 'lower-case'],
    'type-empty': [2, 'never'],
  },
};
