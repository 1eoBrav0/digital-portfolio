export const levels=[
['#######','#     #','# .$@ #','#     #','#######'],
['#######','#  .  #','#  $  #','#  @  #','#     #','#######'],
['########','# .  . #','# $  $ #','#   @  #','#      #','########'],
['########','#      #','# .##. #','# $  $ #','#  @   #','#      #','########'],
['########','# . .  #','# $ $  #','#  #   #','#  @   #','#      #','########'],
['########','#      #','# . . .#','# $ $ $#','#   @  #','#      #','########']];
export function start(index){const rows=levels[index];if(!rows)throw Error('Unknown level');let player='',crates=[],goals=[],walls=[];rows.forEach((r,y)=>[...r].forEach((c,x)=>{const k=x+','+y;if(c==='#')walls.push(k);if(c==='$'||c==='*')crates.push(k);if(c==='.'||c==='*'||c==='+')goals.push(k);if(c==='@'||c==='+')player=k;}));return{width:rows[0].length,height:rows.length,player,crates,goals,walls,moves:0,pushes:0};}
export function move(state,dx,dy){if(Math.abs(dx)+Math.abs(dy)!==1)throw Error('Invalid direction');const [x,y]=state.player.split(',').map(Number);const target=`${x+dx},${y+dy}`;if(x+dx<0||y+dy<0||x+dx>=state.width||y+dy>=state.height||state.walls.includes(target))return state;const crates=[...state.crates];const i=crates.indexOf(target);if(i!==-1){const beyond=`${x+dx*2},${y+dy*2}`;if(state.walls.includes(beyond)||crates.includes(beyond)||x+dx*2<0||y+dy*2<0||x+dx*2>=state.width||y+dy*2>=state.height)return state;crates[i]=beyond;}return{...state,player:target,crates,moves:state.moves+1,pushes:state.pushes+(i!==-1?1:0)};}
export const won=s=>s.crates.every(c=>s.goals.includes(c));
export function solve(initial,limit=60000){let queue=[{s:initial,path:[]}],seen=new Set();for(let i=0;i<queue.length&&i<limit;i++){const {s,path}=queue[i];if(won(s))return path;for(const [dx,dy]of[[0,-1],[0,1],[-1,0],[1,0]]){const n=move(s,dx,dy);const k=n.player+'|'+[...n.crates].sort().join('|');if(n===s||seen.has(k))continue;seen.add(k);queue.push({s:n,path:[...path,[dx,dy]]});}}return null;}
