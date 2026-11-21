const stages=['Запланировано','В работе','Готово'];
const key='serafim-studio-board-v1';
let overrides={};
try{overrides=JSON.parse(localStorage.getItem(key))||{};}catch{}
function render(){
  const area=document.querySelector('.cards');area.replaceChildren();
  for(const stage of stages){
    const col=document.createElement('section');
    const heading=document.createElement('h2');heading.textContent=stage;col.append(heading);
    for(const item of window.initialTasks.filter(t=>(overrides[t.id]||t.stage)===stage)){
      const card=document.createElement('article'),name=document.createElement('strong'),meta=document.createElement('p'),pick=document.createElement('select');
      name.textContent=item.task;meta.textContent=item.owner+' · '+item.due;pick.ariaLabel='Статус: '+item.task;
      for(const s of stages)pick.add(new Option(s,s,false,stage===s));
      pick.onchange=()=>{overrides[item.id]=pick.value;try{localStorage.setItem(key,JSON.stringify(overrides));}catch{}render()};
      card.append(name,meta,pick);col.append(card);
    }
    area.append(col);
  }
}
render();
