module.exports = {
  content: [
    'src/templates/**/*.html',
    'src/static/js/**/*.js'
  ],
  css: ['src/static/css/dashboard.css'],
  safelist: {
    standard: [
      'active',
      'uploading',
      'drag-over',
      'new',
      'ingested',
      'already_exists',
      'error',
      'found',
      'missing',
      'loading'
    ],
    greedy: [/active$/, /card$/]
  },
  extractors: [
    {
      extractor: content => content.match(/[A-Za-z0-9-_:/]+/g) || [],
      extensions: ['html', 'js']
    }
  ],
  output: 'src/static/css/dashboard.min.css'
}
