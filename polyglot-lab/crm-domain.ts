import { DatabaseSync } from 'node:sqlite';
export const stages = ['Новая', 'В работе', 'Предложение', 'Завершена'] as const;
export type Stage = typeof stages[number];
export interface Deal {id:number;company:string;title:string;owner:string;amount:number;stage:Stage;due:string;version:number}
export class CRM {
  db:DatabaseSync;
  constructor(path:string) {
    this.db=new DatabaseSync(path);
    this.db.exec(`PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;
      CREATE TABLE IF NOT EXISTS deals(id INTEGER PRIMARY KEY,company TEXT NOT NULL,title TEXT NOT NULL,owner TEXT NOT NULL,amount INTEGER CHECK(amount>=0),stage TEXT NOT NULL,due TEXT NOT NULL,version INTEGER DEFAULT 1);
      CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,deal_id INTEGER REFERENCES deals(id),action TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);`);
  }
  list():Deal[] {return this.db.prepare('SELECT * FROM deals ORDER BY id DESC').all() as unknown as Deal[];}
  add(input:Record<string,unknown>) {
    const {company,title,owner,amount,due}=input;
    if (![company,title,owner].every(v=>typeof v==='string'&&v.trim().length>0&&v.length<=120)) throw Error('Заполните компанию, задачу и ответственного (до 120 символов)');
    if (!Number.isSafeInteger(amount)||Number(amount)<0||Number(amount)>100_000_000) throw Error('Сумма должна быть целым числом от 0 до 100 000 000 ₽');
    if(typeof due!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(due)||new Date(due).toISOString().slice(0,10)!==due)throw Error('Некорректная дата');
    this.db.exec('BEGIN IMMEDIATE');
    try {const r=this.db.prepare('INSERT INTO deals(company,title,owner,amount,stage,due) VALUES(?,?,?,?,?,?)').run(String(company).trim(),String(title).trim(),String(owner).trim(),Number(amount),'Новая',due); const id=Number(r.lastInsertRowid);this.db.prepare('INSERT INTO events(deal_id,action) VALUES(?,?)').run(id,'Заявка создана');this.db.exec('COMMIT');return id;}catch(e){this.db.exec('ROLLBACK');throw e;}
  }
  move(id:number,stage:string,version:number) {
    if(!stages.includes(stage as Stage))throw Error('Неизвестный этап');
    this.db.exec('BEGIN IMMEDIATE');
    try {const r=this.db.prepare('UPDATE deals SET stage=?,version=version+1 WHERE id=? AND version=?').run(stage,id,version);if(r.changes!==1)throw Error('Карточка изменена другим пользователем. Обновите страницу.');this.db.prepare('INSERT INTO events(deal_id,action) VALUES(?,?)').run(id,`Этап: ${stage}`);this.db.exec('COMMIT');}catch(e){this.db.exec('ROLLBACK');throw e;}
  }
  seed(){if(this.list().length)return;const companies=['Линия','Северный свет','Мастерская 12','Точка роста','Орион','Кедр','Вектор','Форма'];const titles=['Настройка записи клиентов','Сайт сервисного центра','Импорт клиентской базы','Автоматизация отчёта','Личный кабинет','Интеграция склада','Согласование заявок','Поддержка магазина'];for(let i=0;i<8;i++){const id=this.add({company:companies[i],title:titles[i],owner:['Анна','Марк','Ирина'][i%3],amount:[28000,45000,18000,32000,60000,24000,39000,16000][i],due:`2026-11-${23+i}`});this.move(id,stages[Math.floor(i/2)],1);}}
  close(){this.db.close();}
}
