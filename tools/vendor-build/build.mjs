// Bundles frontend dependencies into static/vendor so ConvoAI runs fully offline.
import { build } from 'esbuild';
import { cpSync, mkdirSync, writeFileSync } from 'node:fs';

const out = '../../static/vendor';
mkdirSync(`${out}/fonts`, { recursive: true });

// Material Web (all components + typography styles) as one ES module
await build({
  stdin: {
    contents: `export * from '@material/web/all.js';
import {styles as typescaleStyles} from '@material/web/typography/md-typescale-styles.js';
document.adoptedStyleSheets.push(typescaleStyles.styleSheet);`,
    resolveDir: '.',
  },
  bundle: true, format: 'esm', minify: true,
  outfile: `${out}/material-web.js`,
});

cpSync('node_modules/chart.js/dist/chart.umd.min.js', `${out}/chart.umd.min.js`);
cpSync('node_modules/marked/lib/marked.umd.js', `${out}/marked.umd.js`);

cpSync('node_modules/material-symbols/material-symbols-rounded.woff2', `${out}/fonts/material-symbols-rounded.woff2`);
cpSync('node_modules/@fontsource/roboto/files/roboto-latin-400-normal.woff2', `${out}/fonts/roboto-400.woff2`);
cpSync('node_modules/@fontsource/roboto/files/roboto-latin-500-normal.woff2', `${out}/fonts/roboto-500.woff2`);
cpSync('node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2', `${out}/fonts/inter-var.woff2`);

writeFileSync(`${out}/fonts.css`, `
@font-face{font-family:'Inter';font-style:normal;font-weight:100 900;font-display:swap;src:url(fonts/inter-var.woff2) format('woff2')}
@font-face{font-family:'Roboto';font-style:normal;font-weight:400;font-display:swap;src:url(fonts/roboto-400.woff2) format('woff2')}
@font-face{font-family:'Roboto';font-style:normal;font-weight:500;font-display:swap;src:url(fonts/roboto-500.woff2) format('woff2')}
@font-face{font-family:'Material Symbols Rounded';font-style:normal;font-weight:100 700;font-display:block;src:url(fonts/material-symbols-rounded.woff2) format('woff2')}
.material-symbols-rounded{font-family:'Material Symbols Rounded';font-weight:normal;font-style:normal;font-size:24px;line-height:1;letter-spacing:normal;text-transform:none;display:inline-block;white-space:nowrap;word-wrap:normal;direction:ltr;-webkit-font-smoothing:antialiased;font-feature-settings:'liga'}
`);
console.log('vendor assets written to static/vendor');
