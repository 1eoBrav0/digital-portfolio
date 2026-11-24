const formats={post:['Публикация · 1080 × 1350','Кофейная коллекция Ser — Медленное утро'],story:['История · 1080 × 1920','Вертикальная история Ser Coffee'],cover:['Широкая обложка · 1920 × 768','Обложка Ser Coffee'],icons:['Набор иконок · 1080 × 1080','Девять векторных иконок Ser Coffee']};
document.querySelectorAll('[data-format]').forEach(button=>button.addEventListener('click',()=>{
  const key=button.dataset.format;
  document.querySelectorAll('[data-format]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  const img=document.querySelector('#graphic-preview');img.src=`social-kit/${key}.png`;img.alt=formats[key][1];
  document.querySelector('#png-download').href=`social-kit/${key}.png`;
  document.querySelector('#svg-download').href=`social-kit/${key}.svg`;
  document.querySelector('#format-caption').textContent=formats[key][0];
}));
const report=window.SER_REPORT;
const labels={accepted:'Принят',duplicate:'Повтор',rejected:'Отклонён'};
const reasons={'Same ID has conflicting content':'Конфликт содержимого','Unknown SKU: MISSING':'Неизвестный товар','Insufficient stock: CUP-01':'Недостаточно остатков','Quantity must be an integer from 1 to 10000':'Дробное количество'};
const money=n=>new Intl.NumberFormat('ru-RU',{style:'currency',currency:'RUB',maximumFractionDigits:0}).format(n/100);
document.querySelector('#replay').addEventListener('click',async()=>{
  const button=document.querySelector('#replay');button.disabled=true;button.textContent='Проверка…';
  const body=document.querySelector('#event-rows');body.replaceChildren();
  document.querySelector('#orders-count').textContent='0';document.querySelector('#sum-count').textContent='0 ₽';document.querySelector('#reject-count').textContent='0';
  document.querySelector('#delivery').textContent='Получатель: ожидание';
  const reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let accepted=0,rejected=0,total=0;
  for(const event of report.events){
    const tr=document.createElement('tr');
    const id=document.createElement('td');id.textContent=event.id;
    const status=document.createElement('td');const badge=document.createElement('span');badge.className=`result ${event.status}`;badge.textContent=labels[event.status];status.append(badge);
    const detail=document.createElement('td');detail.textContent=event.reason?reasons[event.reason]||event.reason:event.status==='duplicate'?'Повторно не списано':money(event.total_kopecks);
    tr.append(id,status,detail);body.append(tr);
    if(event.status==='accepted'){accepted++;total+=event.total_kopecks;}if(event.status==='rejected')rejected++;
    document.querySelector('#orders-count').textContent=accepted;document.querySelector('#sum-count').textContent=money(total);document.querySelector('#reject-count').textContent=rejected;
    document.querySelector('#run-status').textContent=`Обработка ${event.id}: ${labels[event.status].toLowerCase()}.`;
    if(!reduce)await new Promise(resolve=>setTimeout(resolve,180));
  }
  document.querySelector('#run-status').textContent='Доставка: имитация timeout. Заказы остаются в очереди.';
  document.querySelector('#delivery').textContent=`Очередь повторов: ${report.after_timeout.orders.length}`;
  if(!reduce)await new Promise(resolve=>setTimeout(resolve,850));
  document.querySelector('#run-status').textContent='Повторная доставка успешна. Восемь событий дали три заказа без повторного списания.';
  document.querySelector('#delivery').textContent=`Получатель: ${report.receiver_count} заказа · по 2 попытки`;
  button.textContent='Повторить проверку';button.disabled=false;
});
