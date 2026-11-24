import * as THREE from 'three';

// One design unit is 5 cm: the board is 46 × 46 cm. Export converts to metres.
// Original parametric geometry; no downloaded meshes or photographic textures.
export function createChess() {
  const root = new THREE.Group(); root.name = 'Ser Chess — Atelier';
  root.userData = {designUnitCentimetres:5, boardWidthCm:46, squareWidthCm:5, pieces:32, license:'MIT', design:'Original parametric study; not a manufactured product'};
  const mat = (name, color, metalness=0, roughness=.3) => new THREE.MeshStandardMaterial({name,color,metalness,roughness});
  const materials = {
    ivory:mat('Warm ivory resin',0xe9dfca,.05,.24), ebony:mat('Polished ebony',0x262b2b,.15,.22),
    brass:mat('Brushed champagne brass',0xb8a36e,.78,.29), walnut:mat('Walnut frame',0x39261f,.05,.4),
    light:mat('Maple inlay',0xcdbb92,.04,.47), dark:mat('Smoked walnut inlay',0x504338,.04,.43),
    lightGrain:mat('Maple grain',0xbfae89,.04,.47), darkGrain:mat('Walnut grain',0x584a3e,.04,.43),
    felt:mat('Charcoal felt',0x182225,0,.93), eye:mat('Obsidian detail',0x101517,.2,.16)
  };
  const add = (group, geometry, material, name, pos=[0,0,0]) => {
    const mesh = new THREE.Mesh(geometry,material); mesh.name=name; mesh.position.set(...pos);
    mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);return mesh;
  };
  const box = (g,size,m,name,pos) => add(g,new THREE.BoxGeometry(...size),m,name,pos);
  const ring = (g,r,y,m,t=.018) => {const a=add(g,new THREE.TorusGeometry(r,t,8,48),m,'Turned decorative ring',[0,y,0]);a.rotation.x=Math.PI/2;return a;};
  const lathe = (g,points,m,name) => add(g,new THREE.LatheGeometry(points.map(([r,y])=>new THREE.Vector2(r,y)),64),m,name);
  const sphere = (g,r,m,name,pos) => add(g,new THREE.SphereGeometry(r,24,16),m,name,pos);
  function bevelBlock(g,w,d,h,r,m,name,y) {
    const s=new THREE.Shape(); const x=-w/2,z=-d/2;
    s.moveTo(x+r,z);s.lineTo(x+w-r,z);s.quadraticCurveTo(x+w,z,x+w,z+r);
    s.lineTo(x+w,z+d-r);s.quadraticCurveTo(x+w,z+d,x+w-r,z+d);
    s.lineTo(x+r,z+d);s.quadraticCurveTo(x,z+d,x,z+d-r);
    s.lineTo(x,z+r);s.quadraticCurveTo(x,z,x+r,z);
    const geo=new THREE.ExtrudeGeometry(s,{depth:h,bevelEnabled:true,bevelSize:.025,bevelThickness:.025,bevelSegments:3,steps:1,curveSegments:6});
    geo.rotateX(-Math.PI/2); return add(g,geo,m,name,[0,y,0]);
  }
  const board=new THREE.Group();board.name='Board · 46 cm';root.add(board);
  bevelBlock(board,9.2,9.2,.31,.12,materials.walnut,'Rounded walnut foundation',-.36);
  bevelBlock(board,9.1,9.1,.025,.09,materials.brass,'Continuous brass reveal',-.09);
  bevelBlock(board,9.13,9.13,.05,.10,materials.walnut,'Walnut top frame',-.06);
  for(const x of [-3.8,3.8])for(const z of [-3.8,3.8]){
    add(board,new THREE.CylinderGeometry(.25,.29,.1,32),materials.felt,'Felt foot',[x,-.42,z]);
  }
  for(let z=0;z<8;z++)for(let x=0;x<8;x++){
    const square=box(board,[.994,.05,.994],((x+z)%2===0)?materials.light:materials.dark,`Square ${'abcdefgh'[x]}${8-z}`,[x-3.5,.015,z-3.5]);
    square.userData.square=true;
    // Fine strips create visible wood grain directly as exportable geometry.
    const grainMat=((x+z)%2===0)?materials.lightGrain:materials.darkGrain;
    for(let k=0;k<5;k++){
      const offset=-.38+k*.19+Math.sin((x+1)*(z+3)+k)*.023;
      const grain=box(board,[.003,.0007,.972],grainMat,'Inlay grain',[x-3.5+offset,.0405,z-3.5]);
      grain.castShadow=false;
    }
  }
  for(const v of [-4.045,4.045]) {box(board,[.016,.012,8.11],materials.brass,'Brass border',[v,.02,0]);box(board,[8.11,.012,.016],materials.brass,'Brass border',[0,.02,v]);}
  // Minimal geometric coordinate engravings, included in the exported model.
  const strokes={a:[[0,0,.08,.18],[.08,.18,.16,0],[.035,.07,.125,.07]],b:[[0,0,0,.18],[0,.18,.12,.18],[.12,.18,.14,.10],[.14,.10,0,.09],[0,.09,.13,.09],[.13,.09,.14,0],[.14,0,0,0]],c:[[.14,.17,.02,.18],[.02,.18,0,0],[0,0,.14,.01]],d:[[0,0,0,.18],[0,.18,.12,.15],[.12,.15,.14,.03],[.14,.03,0,0]],e:[[0,0,0,.18],[0,.18,.14,.18],[0,.09,.11,.09],[0,0,.14,0]],f:[[0,0,0,.18],[0,.18,.14,.18],[0,.09,.11,.09]],g:[[.14,.17,.02,.18],[.02,.18,0,0],[0,0,.14,0],[.14,0,.14,.08],[.14,.08,.08,.08]],h:[[0,0,0,.18],[.14,0,.14,.18],[0,.09,.14,.09]]};
  for(let i=0;i<8;i++)for(const side of [-1,1])for(const [a,b,c,d] of strokes['abcdefgh'[i]]){
    const p1=new THREE.Vector3(i-3.57+a,.025,side*4.24+b),p2=new THREE.Vector3(i-3.57+c,.025,side*4.24+d);
    const line=add(board,new THREE.CylinderGeometry(.004,.004,p1.distanceTo(p2),5),materials.brass,'Engraved file '+ 'abcdefgh'[i]);
    line.position.copy(p1).add(p2).multiplyScalar(.5);line.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),p2.clone().sub(p1).normalize());
  }
  function base(g,m,r=.34){
    lathe(g,[[0,0],[r*.84,0],[r,.035],[r,.085],[r*.97,.12],[r*.88,.15],[r*.82,.19],[r*.76,.21],[r*.76,.25],[r*.62,.28]],m,'Turned base');
    ring(g,r*.94,.115,materials.brass,.012);
    add(g,new THREE.CylinderGeometry(r*.80,r*.80,.015,40),materials.felt,'Felt base',[0,-.008,0]);
  }
  function body(g,m,h,r=.34){
    base(g,m,r);lathe(g,[[r*.62,.27],[r*.51,.34],[r*.40,.46],[r*.34,h*.67],[r*.43,h*.78],[r*.66,h*.80],[r*.69,h*.84],[r*.58,h*.87],[r*.35,h*.88]],m,'Turned stem');
    ring(g,r*.62,h*.815,materials.brass,.010);
  }
  function knight(g,m){
    base(g,m,.34);
    const shape=new THREE.Shape();
    shape.moveTo(-.24,.26);shape.bezierCurveTo(-.27,.49,-.18,.63,-.22,.82);
    shape.bezierCurveTo(-.34,1.04,-.26,1.31,-.11,1.40);
    shape.lineTo(-.05,1.55);shape.lineTo(.025,1.43);shape.lineTo(.12,1.47);
    shape.lineTo(.16,1.30);shape.bezierCurveTo(.27,1.24,.32,1.14,.46,1.08);
    shape.lineTo(.48,.96);shape.lineTo(.39,.90);shape.lineTo(.20,.96);
    shape.bezierCurveTo(.19,.81,.02,.72,.08,.57);shape.bezierCurveTo(.10,.46,.22,.42,.24,.27);shape.closePath();
    const geo=new THREE.ExtrudeGeometry(shape,{depth:.24,bevelEnabled:true,bevelThickness:.045,bevelSize:.035,bevelSegments:3,curveSegments:10,steps:1});geo.translate(0,0,-.12);geo.computeVertexNormals();
    add(g,geo,m,'Sculpted knight profile');
    for(const side of [-1,1]){
      sphere(g,.022,materials.eye,'Knight eye',[.10,1.26,side*.169]);
      sphere(g,.013,materials.eye,'Knight nostril',[.38,1.055,side*.168]);
    }
    for(let k=0;k<7;k++){
      const mane=box(g,[.055,.075,.30],m,'Carved mane ridge',[-.23+k*.009,.80+k*.075,0]);mane.rotation.z=-.22+k*.075;
    }
    ring(g,.19,.28,materials.brass,.011);
    g.rotation.y=Math.PI/2;
  }
  function makePiece(type,colour,x,z){
    const g=new THREE.Group();g.name=`${colour} ${type} ${'abcdefgh'[x]}${8-z}`;g.userData={piece:true,type,colour,home:[x-3.5,.06,z-3.5]};
    const m=materials[colour];
    if(type==='Pawn'){
      body(g,m,.83,.28);sphere(g,.17,m,'Pawn head',[0,.87,0]);
    } else if(type==='Rook'){
      base(g,m,.34);lathe(g,[[.22,.27],[.17,.35],[.15,.92],[.23,.99],[.25,1.04],[.25,1.12],[.21,1.15],[.17,1.15],[.17,1.03],[.12,1.03],[0,1.03]],m,'Rook tower');
      for(let k=0;k<6;k++){const a=k*Math.PI/3;const b=box(g,[.13,.17,.14],m,'Castle battlement',[Math.sin(a)*.20,1.19,Math.cos(a)*.20]);b.rotation.y=a;}
      ring(g,.235,1.02,materials.brass,.012);
    }else if(type==='Knight'){knight(g,m);if(colour==='ebony')g.rotation.y=-Math.PI/2;
    }else if(type==='Bishop'){
      body(g,m,1.10,.33);
      // Two separate mitre lobes form a real diagonal slit, not a painted line.
      const mitre=new THREE.Group();mitre.position.y=1.11;mitre.rotation.z=-.26;g.add(mitre);
      const profile=[[0,-.18],[.11,-.15],[.18,-.03],[.16,.10],[.08,.24],[0,.30]];
      for(const side of [-1,1]){
        const geo=new THREE.LatheGeometry(profile.map(([r,y])=>new THREE.Vector2(r,y)),32,side===1?0:Math.PI,Math.PI-.10);
        geo.rotateZ(Math.PI/2);const mtr=add(mitre,geo,m,'Split bishop mitre');mtr.rotation.z=-Math.PI/2;
      }
      sphere(g,.042,m,'Bishop finial',[.075,1.415,0]);
    }else if(type==='Queen'){
      body(g,m,1.35,.36);
      lathe(g,[[.13,1.18],[.18,1.30],[.25,1.48],[.24,1.50],[.19,1.46],[.12,1.31],[0,1.31]],m,'Open royal crown');
      for(let k=0;k<8;k++){const a=k*Math.PI/4;const tooth=add(g,new THREE.ConeGeometry(.047,.17,12),m,'Crown point',[Math.sin(a)*.23,1.52,Math.cos(a)*.23]);sphere(g,.038,materials.brass,'Crown pearl',[Math.sin(a)*.23,1.62,Math.cos(a)*.23]);}
      sphere(g,.065,m,'Queen central finial',[0,1.47,0]);
    }else{
      body(g,m,1.47,.37);lathe(g,[[.13,1.27],[.20,1.35],[.21,1.41],[.15,1.46],[.12,1.48]],m,'King crown');
      sphere(g,.085,m,'King orb',[0,1.50,0]);
      box(g,[.085,.32,.085],m,'King vertical cross',[0,1.71,0]);box(g,[.25,.085,.085],m,'King horizontal cross',[0,1.76,0]);
      ring(g,.19,1.40,materials.brass,.011);
    }
    g.position.set(x-3.5,.06,z-3.5);root.add(g);return g;
  }
  const order=['Rook','Knight','Bishop','Queen','King','Bishop','Knight','Rook'];
  for(let x=0;x<8;x++)for(const [colour,back,pawn] of [['ebony',0,1],['ivory',7,6]]) {makePiece(order[x],colour,x,back);makePiece('Pawn',colour,x,pawn);}
  root.updateMatrixWorld(true);
  return {root,materials,board,pieces:root.children.filter(x=>x.userData.piece)};
}
