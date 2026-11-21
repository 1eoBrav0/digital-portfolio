import fs from 'node:fs';
const [source='orders.json',target='board-data.js']=process.argv.slice(2);
const stages=['Запланировано','В работе','Готово'];
const tasks=new Map();
for(const row of JSON.parse(fs.readFileSync(source,'utf8'))){
 if(!['id','task','owner','due'].every(k=>typeof row[k]==='string'&&row[k].trim())||!stages.includes(row.stage)) throw Error('Некорректная заявка');
 if(tasks.has(row.id)&&JSON.stringify(tasks.get(row.id))!==JSON.stringify(row)) throw Error('Конфликт ID '+row.id);
 tasks.set(row.id,row);
}
const output='window.initialTasks = '+JSON.stringify([...tasks.values()],null,2)+';\n';
if(!fs.existsSync(target)||fs.readFileSync(target,'utf8')!==output){
 const temp=target+'.'+process.pid+'.tmp';fs.writeFileSync(temp,output);fs.renameSync(temp,target);
}
console.log('Задач на доске:',tasks.size);
