import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.mp4':'video/mp4','.wav':'audio/wav'};
http.createServer((req,res)=>{
  let filename;
  try {filename=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));} catch {res.writeHead(400).end();return;}
  if(filename!==root&&!filename.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  if(filename===root||filename.endsWith(path.sep))filename=path.join(filename,'index.html');
  fs.stat(filename,(err,stat)=>{
    if(err||!stat.isFile()){res.writeHead(404).end('Not found');return;}
    res.writeHead(200,{'Content-Type':mime[path.extname(filename)]||'application/octet-stream','Content-Length':stat.size});
    fs.createReadStream(filename).pipe(res);
  });
}).listen(8787,'127.0.0.1',()=>console.log('Portfolio preview: http://127.0.0.1:8787'));
