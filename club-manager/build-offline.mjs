import {readFile,writeFile} from 'node:fs/promises';
import vm from 'node:vm';
const read = name => readFile(new URL(name, import.meta.url),'utf8');
let html = await read('index.html');
const code = (await Promise.all(['model.js','data.js','app.js'].map(read)))
  .map(source => source.replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,''))
  .join('\n');
new vm.Script(code);
const css = await read('style.css');
const logo = await readFile(new URL('ser-black.png',import.meta.url));
html = html.replace('<link rel="stylesheet" href="style.css">',`<style>${css}</style>`)
  .replace('src="ser-black.png"',`src="data:image/png;base64,${logo.toString('base64')}"`)
  .replace('<script type="module" src="app.js"></script>',`<script>(()=>{${code.replace(/<\/script/gi,'<\\/script')}\n})();</script>`);
await writeFile(new URL('Ser-Club.html',import.meta.url),html);
console.log('Ser-Club.html: self-contained; JavaScript syntax verified');
