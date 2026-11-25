export const initialCampaigns = [
  {name:'Районные Telegram-каналы',audience:'Жители в радиусе 15–20 минут от клуба',budget:4500,cpc:25,conversion:0.08,attendance:0.8},
  {name:'Локальные игровые сообщества',audience:'Игроки CS2 и команды Москвы',budget:3000,cpc:30,conversion:0.10,attendance:0.8},
  {name:'Повторное размещение победителя',audience:'Площадка с подтверждёнными визитами',budget:1500,cpc:20,conversion:0.06,attendance:0.8}
];
export const initialSettings={pcs:20,hours:12,days:30,baseline:50,visitHours:4,rate:200,variableCost:35,managementCost:0};
export function forecast(campaigns,settings){
  const s={...initialSettings,...settings};
  for(const k of ['pcs','hours','days','visitHours','rate']) if(!Number.isFinite(s[k])||s[k]<=0) throw Error('Положительное значение: '+k);
  if(![s.baseline,s.variableCost,s.managementCost].every(Number.isFinite)||s.hours>24||s.baseline<0||s.baseline>100||s.variableCost<0||s.managementCost<0) throw Error('Недопустимые условия');
  const rows=campaigns.map(c=>{if(c.budget<0||c.cpc<=0||c.conversion<0||c.conversion>1||c.attendance<0||c.attendance>1||![c.budget,c.cpc,c.conversion,c.attendance].every(Number.isFinite))throw Error('Проверьте рекламные допущения'); const clicks=c.budget/c.cpc; const bookings=clicks*c.conversion; return {...c,clicks,bookings,visits:bookings*c.attendance};});
  const spend=rows.reduce((a,c)=>a+c.budget,0), visits=rows.reduce((a,c)=>a+c.visits,0), bookings=rows.reduce((a,c)=>a+c.bookings,0),clicks=rows.reduce((a,c)=>a+c.clicks,0);
  const capacity=s.pcs*s.hours*s.days,baselineHours=capacity*s.baseline/100;
  const demandHours=visits*s.visitHours,addedHours=Math.min(demandHours,capacity-baselineHours),servedVisits=addedHours/s.visitHours;
  const revenue=addedHours*s.rate,contribution=addedHours*(s.rate-s.variableCost)-spend-s.managementCost;
  const marginPerVisit=s.visitHours*(s.rate-s.variableCost);
  return {rows,spend,visits,servedVisits,bookings,clicks,capacity,baselineHours,demandHours,addedHours,revenue,contribution,occupancy:(baselineHours+addedHours)/capacity*100,cac:servedVisits?spend/servedVisits:null,breakEven:marginPerVisit>0?(spend+s.managementCost)/marginPerVisit:null,reserve:10000-spend};
}
export function register(list,entry,limit=20){
  if(list.some(r=>r.id===entry.id))return {list,status:'duplicate'};
  const count=list.filter(r=>r.status==='Подтверждён').length;
  const row={...entry,status:count<limit?'Подтверждён':'Лист ожидания'};
  return {list:[...list,row],status:row.status};
}
export function occupancyGrid(){return Array.from({length:7},(_,d)=>[25,50,75].map((v,h)=>Math.min(100,v+(d>4?15:0)+(d===2&&h===0?5:0))));}
