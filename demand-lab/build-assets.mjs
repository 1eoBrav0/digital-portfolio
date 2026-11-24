import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const sharp=require('sharp');
const root=path.dirname(fileURLToPath(import.meta.url));
const logo=await fs.readFile(path.join(root,'assets/ser-black.png'));
const mark=(x,y,w=150)=>`<image href="data:image/png;base64,${logo.toString('base64')}" x="${x}" y="${y}" width="${w}" height="${w/2}"/>`;
const wrap=(w,h,body,bg='#f3f0e9')=>`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><rect width="100%" height="100%" fill="${bg}"/><g font-family="Arial, sans-serif" fill="#152c27">${body}</g></svg>`;
const text=(x,y,s,size=60,extra='')=>`<text x="${x}" y="${y}" font-size="${size}" ${extra}>${s}</text>`;
const cup=(x,y,scale=1)=>`<g transform="translate(${x} ${y}) scale(${scale})"><ellipse cx="215" cy="438" rx="225" ry="38" fill="#193e35" opacity=".14"/><path d="M370 120 H425 Q530 120 510 230 Q495 308 388 308" fill="none" stroke="#f4e4c4" stroke-width="40"/><path d="M20 85 H390 L361 366 Q354 424 290 430 H116 Q54 424 47 366Z" fill="#faf2df"/><path d="M49 110 H363 L341 350 Q336 386 311 397 H89 Q73 383 70 352Z" fill="#e7d5b3"/><ellipse cx="205" cy="88" rx="185" ry="48" fill="#fff8e8"/><ellipse cx="205" cy="90" rx="161" ry="33" fill="#8c4b2e"/><ellipse cx="205" cy="88" rx="139" ry="22" fill="#a76a42"/><path d="M147 87 Q200 45 259 87 Q212 121 175 84 Q219 65 237 91" fill="none" stroke="#ebcf9e" stroke-width="8" stroke-linecap="round"/><path d="M180 -30 C130 -80 220 -100 175 -160 M245 -15 C205 -60 295 -100 245 -145" fill="none" stroke="#7c9562" stroke-width="9" stroke-linecap="round"/></g>`;
async function save(folder,name,svg){await fs.mkdir(path.join(root,folder),{recursive:true});await fs.writeFile(path.join(root,folder,name+'.svg'),svg);await sharp(Buffer.from(svg)).png().toFile(path.join(root,folder,name+'.png'));}
await save('social-kit','post',wrap(1080,1350,`${mark(72,45,160)}${text(72,190,'КОФЕЙНАЯ КОЛЛЕКЦИЯ / КОНЦЕПТ',22,'letter-spacing="3"')}${text(66,335,'Медленное',100,'font-weight="700"')}${text(66,442,'утро.',132,'font-weight="700"')}<circle cx="538" cy="875" r="330" fill="#c9d4a5"/>${cup(275,650,1.1)}${text(72,1225,'Пауза, которую можно почувствовать.',34)}${text(72,1288,'ДЕМОНСТРАЦИОННЫЙ МАКЕТ',19,'letter-spacing="3"')}`));
await save('social-kit','story',wrap(1080,1920,`${mark(80,100,170)}${text(80,335,'ДЛЯ ТЕХ, КТО',35,'letter-spacing="5"')}${text(72,470,'не спешит.',122,'font-weight="700"')}<circle cx="530" cy="1020" r="390" fill="#c9d4a5"/>${cup(240,800,1.25)}${text(80,1490,'Начни с маленькой паузы.',44)}<rect x="80" y="1570" width="920" height="130" rx="65" fill="#193e35"/>${text(540,1650,'ТВОЁ МЕДЛЕННОЕ УТРО',31,'text-anchor="middle" fill="#fff8e8" letter-spacing="3"')}${text(80,1790,'SER / ВЫМЫШЛЕННАЯ КОФЕЙНАЯ КОЛЛЕКЦИЯ',20,'letter-spacing="2"')}`));
await save('social-kit','cover',wrap(1920,768,`${mark(100,60,170)}${text(100,280,'Медленное утро.',112,'font-weight="700"')}${text(106,370,'Маленький ритуал. Большая пауза.',39)}${text(106,645,'SER COFFEE / ДЕМОНСТРАЦИОННЫЙ КОНЦЕПТ',22,'letter-spacing="3"')}<circle cx="1450" cy="400" r="350" fill="#c9d4a5"/>${cup(1205,270,.92)}`));
const paths=[
['cup','M18 28H70L65 63Q64 72 54 72H34Q24 72 23 63ZM70 33H78Q91 33 85 49Q82 56 68 56 M38 17V8 M51 17V8'],
['bean','M70 18C45 3 9 43 23 70C40 92 85 54 70 18Z M64 20C33 35 66 48 29 69'],
['clock','M48 17A31 31 0 1 0 48 79A31 31 0 1 0 48 17 M48 28V49L63 57'],
['leaf','M20 76C12 30 35 15 78 17C80 60 57 82 20 76Z M23 73L65 31'],
['drop','M48 14C40 30 22 43 22 59A26 26 0 0 0 74 59C74 43 57 28 48 14Z M35 57Q34 68 46 70'],
['bag','M27 29H69L76 79H20Z M37 29V22A11 11 0 0 1 59 22V29'],
['filter','M17 23H79L58 55V77H39V55Z M25 35H71'],
['spark','M48 13V28 M48 68V83 M13 48H28 M68 48H83 M25 25L35 35 M61 61L71 71 M25 71L35 61 M61 35L71 25'],
['heart','M48 77L20 49C0 25 29 9 48 31C67 9 96 25 76 49Z']
];
await fs.mkdir(path.join(root,'social-kit/icons'),{recursive:true});
for(const [name,d] of paths)await fs.writeFile(path.join(root,'social-kit/icons',name+'.svg'),`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><path d="${d}" fill="none" stroke="#193e35" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>`);
await save('social-kit','icons',wrap(1080,1080,`${mark(65,40,130)}${text(70,175,'Детали одного ритуала',44,'font-weight="700"')}${paths.map(([name,d],i)=>`<g transform="translate(${130+(i%3)*330} ${260+Math.floor(i/3)*265})"><rect x="-25" y="-25" width="220" height="210" rx="40" fill="#e0e6cc"/><g transform="scale(1.7)"><path d="${d}" fill="none" stroke="#193e35" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></g></g>`).join('')}`));
const scenes=[
['Идея.','Кадр.','Движение.','РОЛИК, КОТОРЫЙ МОЖНО ПОКАЗАТЬ'],
['Сначала —','смысл.','','ОДНА МЫСЛЬ. НИЧЕГО ЛИШНЕГО.'],
['Потом —','ритм.','','ТИПОГРАФИКА В ДВИЖЕНИИ'],
['Текст.','Форма.','Характер.','ГРАФИКА ДЛЯ МАЛЕНЬКОГО ЭКРАНА'],
['30 секунд.','Одна','история.','ВЕРТИКАЛЬНЫЙ ФОРМАТ 9:16'],
['Покажи','свою','идею.','SER / MOTION STUDY']
];
for(let i=0;i<scenes.length;i++){
const [a,b,c,sub]=scenes[i], bg=i%2?'#b8caf0':'#d8ed8c';
const shapes=i%3===0?'<circle cx="810" cy="1260" r="380" fill="#182a21"/><circle cx="810" cy="1260" r="245" fill="'+bg+'"/><circle cx="810" cy="1260" r="110" fill="#182a21"/>':i%3===1?'<g fill="#182a21"><rect x="90" y="1100" width="185" height="470" rx="92"/><rect x="350" y="1000" width="185" height="670" rx="92"/><rect x="610" y="1150" width="185" height="370" rx="92"/><rect x="870" y="1080" width="185" height="510" rx="92"/></g>':'<g fill="none" stroke="#182a21" stroke-width="40"><ellipse cx="540" cy="1280" rx="440" ry="290"/><ellipse cx="540" cy="1280" rx="300" ry="290"/><ellipse cx="540" cy="1280" rx="150" ry="290"/></g>';
await save('motion/frames',`scene-${i+1}`,wrap(1080,1920,`${mark(70,90,170)}${text(80,285,'MOTION STUDY / DEMO',24,'letter-spacing="5"')}${text(72,485,a,112,'font-weight="700"')}${text(72,620,b,112,'font-weight="700"')}${text(72,755,c,112,'font-weight="700"')}${shapes}<rect x="80" y="1720" width="920" height="2" fill="#182a21"/>${text(80,1790,sub,23,'letter-spacing="2"')}`,bg));
}
await fs.copyFile(path.join(root,'motion/frames/scene-1.png'),path.join(root,'motion/poster.png'));
console.log('Created 4 graphic layouts, 9 SVG icons and 6 motion scenes.');
