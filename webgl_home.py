"""Lightweight browser-side 3D orientation scene for the logged-in home page."""

from __future__ import annotations

import streamlit.components.v1 as components


def render_orientation_scene(role_label: str) -> None:
    """Render an independent Three.js scene; it does not share simulation state."""
    html = _SCENE_HTML.replace("__ROLE_LABEL__", role_label)
    components.html(html, height=760, scrolling=False)


_SCENE_HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<style>
  :root{--ink:#172b35;--muted:#6e7e85;--line:#dbe4e7;--paper:#f7faf9;--accent:#0d7183;--warn:#d97626}
  *{box-sizing:border-box} html,body{margin:0;height:100%;font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:transparent}
  .shell{height:744px;display:grid;grid-template-columns:64px minmax(0,1fr) 244px;grid-template-rows:minmax(0,1fr) 126px;gap:10px}
  .rail,.stage,.panel,.tasks{border:1px solid rgba(31,62,73,.13);background:rgba(249,251,250,.92);box-shadow:0 18px 54px rgba(25,53,63,.08)}
  .rail{grid-row:1/3;border-radius:20px;padding:15px 8px;display:flex;flex-direction:column;align-items:center;gap:8px}
  .brand{width:42px;height:42px;border-radius:14px;background:#173b49;color:#fff;display:grid;place-items:center;font-weight:800;margin-bottom:12px}
  .rail button{border:0;background:transparent;width:54px;padding:9px 2px;border-radius:12px;color:#708188;font-size:10px;cursor:pointer}
  .rail button span{display:block;font-size:19px;margin-bottom:3px}.rail button.active,.rail button:hover{background:#e6f1f2;color:#0b6575}
  .role{margin-top:auto;font-size:10px;color:#73848b;text-align:center}.role b{display:block;color:#173b49;margin-top:4px}
  .stage{position:relative;overflow:hidden;border-radius:22px;background:linear-gradient(145deg,#edf3f3,#dce8e8)}
  #canvas{position:absolute;inset:0}.stage-head{position:absolute;z-index:3;left:24px;top:20px;pointer-events:none}
  .eyebrow{font-size:11px;letter-spacing:.16em;color:#56717b;font-weight:700}.stage-head h2{font-size:22px;margin:5px 0 4px}.stage-head p{font-size:12px;color:#667a82;margin:0}
  .viewbar{position:absolute;z-index:4;right:16px;top:16px;display:flex;gap:7px}.viewbar button,.reset{border:1px solid rgba(32,61,70,.14);background:rgba(255,255,255,.83);backdrop-filter:blur(9px);border-radius:10px;padding:8px 10px;color:#39535d;cursor:pointer;font-size:11px}.viewbar button:hover{background:#fff;color:#0c7181}
  .hint{position:absolute;z-index:3;left:50%;bottom:13px;transform:translateX(-50%);font-size:11px;color:#5c7078;background:rgba(255,255,255,.82);padding:7px 12px;border-radius:20px;pointer-events:none;white-space:nowrap}
  .label{position:absolute;z-index:4;display:none;transform:translate(-50%,-50%);pointer-events:none;color:#183843;background:#fff;border:1px solid #d9e5e7;border-radius:8px;padding:5px 8px;font-size:10px;box-shadow:0 8px 20px rgba(22,48,57,.13)}
  .panel{border-radius:22px;padding:17px;overflow:hidden}.panel-top{display:flex;align-items:center;justify-content:space-between}.kicker{font-size:9px;letter-spacing:.12em;color:#778b92;font-weight:700}.status{font-size:9px;color:#23785d;background:#e6f4ee;border-radius:10px;padding:5px 7px}
  .panel h3{font-size:18px;line-height:1.25;margin:13px 0 7px}.panel p{font-size:11px;line-height:1.65;color:#63767e;margin:0}.meta{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:14px 0}.meta div{background:#f0f5f4;border-radius:11px;padding:9px}.meta b{display:block;font-size:11px}.meta span{font-size:9px;color:#75868c}
  .tabs{display:flex;gap:5px;border-bottom:1px solid var(--line);margin:10px 0 14px}.tabs button{border:0;background:transparent;padding:8px 7px;color:#75868d;font-size:11px;cursor:pointer;border-bottom:2px solid transparent}.tabs button.active{color:#0b6e7e;border-color:#0b6e7e}
  .detail{min-height:142px}.detail h4{font-size:13px;margin:0 0 8px}.detail ul{margin:0;padding-left:17px;color:#60747c;font-size:11px;line-height:1.75}.notice{border-left:3px solid #df8a35;background:#fbf4e8;border-radius:0 9px 9px 0;padding:9px 10px;color:#75552f;font-size:10px;line-height:1.55;margin-top:12px}
  .tasks{grid-column:2/4;border-radius:18px;padding:13px 16px;display:flex;gap:10px;align-items:stretch;overflow:hidden}.task-lead{min-width:160px;padding:7px 8px}.task-lead b{font-size:13px}.task-lead p{font-size:10px;color:#788990;line-height:1.5;margin:5px 0}.task{min-width:142px;flex:1;border:1px solid #dce5e7;border-radius:13px;background:#fff;padding:11px 12px;cursor:pointer;text-align:left;transition:.2s}.task:hover,.task.active{transform:translateY(-2px);border-color:#7fb7bf;box-shadow:0 8px 22px rgba(24,83,94,.10)}.task small{font-size:9px;color:#849298}.task b{display:block;font-size:12px;margin:5px 0}.badge{display:inline-block;border-radius:8px;background:#edf4f5;color:#37636c;padding:3px 6px;font-size:9px}.badge.dual{background:#f7eee5;color:#9a5e26}
  @media(max-width:720px){.shell{height:920px;grid-template-columns:56px 1fr;grid-template-rows:500px 285px 115px}.panel{grid-column:2;grid-row:2}.tasks{grid-column:1/3;grid-row:3}.rail{grid-row:1/3}.task:nth-of-type(n+4){display:none}.stage-head h2{font-size:18px}.viewbar button{padding:7px}}
</style>
</head>
<body>
<div class="shell">
  <nav class="rail">
    <div class="brand">HV</div>
    <button class="active"><span>⌂</span>首页</button><button><span>◇</span>场景</button><button><span>≋</span>PDDL</button><button><span>⌁</span>运动</button><button><span>▷</span>仿真</button>
    <div class="role">当前身份<b>__ROLE_LABEL__</b></div>
  </nav>
  <section class="stage">
    <div id="canvas"></div>
    <div class="stage-head"><div class="eyebrow">INTERACTIVE LAB OVERVIEW</div><h2>双臂带电检修工作台</h2><p>选择部件，认识实验对象、协作边界与危险约束</p></div>
    <div class="viewbar"><button data-view="overview">全景</button><button data-view="top">俯视</button><button data-view="robot">双臂</button><button data-view="hazard">危险区</button></div>
    <div class="hint">拖动旋转 · 滚轮缩放 · 点击场景对象查看说明</div>
    <div class="label" id="label"></div>
  </section>
  <aside class="panel">
    <div class="panel-top"><div class="kicker">OBJECT GUIDE</div><div class="status">● 引导场景</div></div>
    <h3 id="title">双臂协作机器人</h3><p id="summary">两条6DOF机械臂共享基座，在同一工作空间内完成独立操作或协同检修。</p>
    <div class="meta"><div><b id="kind">12 DOF</b><span>场景对象</span></div><div><b id="risk">协作避碰</b><span>学习重点</span></div></div>
    <div class="tabs"><button class="active" data-tab="overview">概览</button><button data-tab="action">操作</button><button data-tab="safety">安全</button></div>
    <div class="detail" id="detail"></div>
    <div class="notice">本页用于认知与导航；真实路径验证、碰撞检测和动力学执行将在后续MuJoCo实验页面完成。</div>
  </aside>
  <section class="tasks">
    <div class="task-lead"><b>选择一个教学任务</b><p>观察任务需要的机械臂、工位和安全约束，再进入正式实验。</p></div>
    <button class="task active" data-target="robot"><small>01 · 拆装工位</small><b>熔断器轴向插装</b><span class="badge">单臂可选</span></button>
    <button class="task" data-target="stationE"><small>02 · 协作工位</small><b>导线剥线与端接</b><span class="badge dual">双臂协作</span></button>
    <button class="task" data-target="hazard"><small>03 · 路径规划</small><b>绕开随机带电区</b><span class="badge dual">安全约束</span></button>
    <button class="task" data-target="lines"><small>04 · 高空约束</small><b>高压线下安全作业</b><span class="badge dual">高度限制</span></button>
  </section>
</div>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.165.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.165.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

const host=document.getElementById('canvas'), scene=new THREE.Scene();
scene.background=new THREE.Color(0xe8efef); scene.fog=new THREE.Fog(0xe8efef,5.0,9.5);
const camera=new THREE.PerspectiveCamera(38,host.clientWidth/host.clientHeight,.05,30);
camera.up.set(0,0,1);
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false}); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setSize(host.clientWidth,host.clientHeight); renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap; renderer.outputColorSpace=THREE.SRGBColorSpace; host.appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement); controls.enableDamping=true; controls.dampingFactor=.07; controls.minDistance=2.2; controls.maxDistance=6.5; controls.maxPolarAngle=Math.PI*.48; controls.screenSpacePanning=true;
scene.add(new THREE.HemisphereLight(0xffffff,0x728189,2.0)); const key=new THREE.DirectionalLight(0xfff8ed,3.2); key.position.set(-2,-3,6); key.castShadow=true; key.shadow.mapSize.set(2048,2048); scene.add(key); const fill=new THREE.DirectionalLight(0x9ccddd,1.2); fill.position.set(3,2,4); scene.add(fill);
const clickable=[]; const info={};
function mat(color,metal=.05,rough=.55,opacity=1){return new THREE.MeshStandardMaterial({color,metalness:metal,roughness:rough,transparent:opacity<1,opacity})}
function box(name,size,pos,color,meta,opacity=1){const m=new THREE.Mesh(new THREE.BoxGeometry(...size),mat(color,.08,.55,opacity));m.name=name;m.position.set(...pos);m.castShadow=true;m.receiveShadow=true;scene.add(m);if(meta){clickable.push(m);info[name]=meta}return m}
function cyl(name,r,len,pos,color,rot=[0,0,0],meta=null){const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,len,28),mat(color,.22,.35));m.name=name;m.position.set(...pos);m.rotation.set(...rot);m.castShadow=true;scene.add(m);if(meta){clickable.push(m);info[name]=meta}return m}
function sphere(parent,r,pos,color){const m=new THREE.Mesh(new THREE.SphereGeometry(r,24,18),mat(color,.28,.3));m.position.set(...pos);m.castShadow=true;parent.add(m);return m}
function capsuleBetween(parent,a,b,r,color){const A=new THREE.Vector3(...a),B=new THREE.Vector3(...b),d=A.distanceTo(B);const m=new THREE.Mesh(new THREE.CapsuleGeometry(r,d-2*r,8,20),mat(color,.16,.3));m.position.copy(A).add(B).multiplyScalar(.5);m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),B.clone().sub(A).normalize());m.castShadow=true;parent.add(m);return m}

box('floor',[6.6,5.4,.08],[.2,0,-.12],0xd9e1e1); box('table',[3.7,3.15,.16],[.45,0,.02],0x4b5d63,{title:'扩展检修工作台',summary:'工作台按准备区、拆装区、检测区、绝缘防护区和协作区组织。',kind:'5类工位',risk:'区域对应',overview:['不同颜色标识教学工位','准备区与操作目标保持运输距离','正式实验中坐标与MuJoCo场景一致'],action:['先确定物体所属准备区','再选择对应目标工位','规划运输与回撤路径'],safety:['带电区会占用部分运输通道','不能仅根据末端点判断路线安全']});
// Station pads
const stations=[['stationA','拆装工位',.70,.70,0x4284a2],['stationB','模块检修工位',1.05,.18,0x667178],['stationC','检测操作工位',.85,-.80,0xd06a37],['stationD','绝缘防护工位',.45,.15,0xd1b63d],['stationE','剥线接线协作工位',.62,-.35,0x7165bb]];
stations.forEach(([id,label,x,y,c])=>box(id,[.48,.38,.045],[x,y,.12],c,{title:label,summary:'固定设施与任务目标共同构成可辨识的教学工位。',kind:'教学工位',risk:'目标对准',overview:['工位颜色与后续页面保持一致','点击任务卡可定位相关工位'],action:['从准备区夹取对象','绕开危险区到达工位','完成插装、检测或协作操作'],safety:['进入工位前仍需验证连杆和末端轨迹']},.66));
// Shared-base dual arm, oriented into the workbench.
const robot=new THREE.Group();robot.name='robot';scene.add(robot); clickable.push(robot);info.robot={title:'双臂协作机器人',summary:'两条6DOF机械臂共享基座，既能独立操作，也能在共享区域内分工协作。',kind:'双6DOF',risk:'双臂避碰',overview:['左、右臂各含6个旋转关节','五项任务允许选择单臂','四项任务必须使用双臂协作'],action:['主臂负责搬运、插装或检测','辅臂负责稳定设施或工件','双臂任务禁止降级为单臂'],safety:['共享基座附近需要限制关节姿态','两臂进入同一区域时必须保持间距']};
box('base',[.42,.48,.14],[-1.15,0,.04],0x27373e); const torso=box('torso',[.30,.42,.48],[-1.15,0,.31],0xd9dedf); torso.parent.remove(torso);robot.add(torso);torso.position.set(0,0,.31);
function arm(side){const g=new THREE.Group();g.position.set(0,side*.29,.56);robot.add(g);sphere(g,.13,[0,0,0],0x353f44);const pts=[[0,0,0],[.30,side*.10,.20],[.60,side*.07,.27],[.82,side*.03,.15],[1.0,0,.11]];for(let i=0;i<pts.length-1;i++){capsuleBetween(g,pts[i],pts[i+1],i<2?.075:.055,0xd8ddde);sphere(g,i<2?.09:.068,pts[i+1],0x394348)}const grip=new THREE.Group();grip.position.set(...pts.at(-1));g.add(grip);boxLocal(grip,[.12,.13,.055],[0,0,0],0x202b30);boxLocal(grip,[.12,.025,.12],[.02,.065,-.07],0xaeb7ba);boxLocal(grip,[.12,.025,.12],[.02,-.065,-.07],0xaeb7ba)}
function boxLocal(parent,size,pos,color){const m=new THREE.Mesh(new THREE.BoxGeometry(...size),mat(color,.18,.35));m.position.set(...pos);m.castShadow=true;parent.add(m);return m}arm(1);arm(-1);robot.position.set(-1.15,0,0);
// Hazard volume and dotted perimeter.
const hazard=box('hazard',[.42,.48,.42],[.25,.48,.33],0xee6b32,{title:'随机带电区域',summary:'在准备区和目标工位之间生成的教学禁止区域，用于迫使路径规划产生可见绕行。',kind:'动态约束',risk:'禁止穿越',overview:['位置、尺寸和安全裕度可调','颜色表示风险而不是实体设备','随机种子用于复现实验条件'],action:['比较正Y侧与负Y侧绕行','将路线决策带入运动规划','逐帧检查工具与连杆'],safety:['直接路线可能穿越安全包络','错误路径会在执行前或执行中触发提示']},.24); hazard.material.side=THREE.DoubleSide;
const edge=new THREE.LineSegments(new THREE.EdgesGeometry(hazard.geometry),new THREE.LineDashedMaterial({color:0xf08a37,dashSize:.08,gapSize:.045}));edge.computeLineDistances();hazard.add(edge);
// Overhead conductors.
const lines=new THREE.Group();lines.name='lines';scene.add(lines);clickable.push(lines);info.lines={title:'上方高压线约束',summary:'三根架空导线限制机械臂通过盲目抬高末端来绕开桌面危险区。',kind:'高度约束',risk:'安全包络',overview:['导线颜色与机械臂形成明显区分','透明安全包络大于可见线径','上下约束共同形成三维通道'],action:['先判断侧向绕行是否可用','限制安全高度上限','验证工具长轴是否进入包络'],safety:['越高并不一定越安全','接近包络时应降低高度并重新规划']};
[-.32,0,.32].forEach((z,i)=>{const wire=capsuleBetween(lines,[-.05,-1.45,1.35+Math.abs(i-1)*.08],[-.05,1.45,1.35+Math.abs(i-1)*.08],.025,i===1?0xde4b3f:0xc33b45); wire.name='lines'});
// porcelain supports
[-1.34,1.34].forEach(y=>[-.32,0,.32].forEach((z,i)=>cyl('',.055,.18,[-.05,y,1.49+Math.abs(i-1)*.08],0xf3f4f1,[0,0,0])));

const views={overview:{p:[3.8,-4.2,3.1],t:[.05,0,.38]},top:{p:[.35,-.01,5.5],t:[.25,0,0]},robot:{p:[1.65,-3.2,1.65],t:[-.65,0,.45]},hazard:{p:[2.55,-2.4,2.15],t:[.35,.18,.38]}};
function setView(k){const v=views[k];camera.position.set(...v.p);controls.target.set(...v.t);controls.update()} setView('overview');
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));

let selected='robot',tab='overview'; const ray=new THREE.Raycaster(),mouse=new THREE.Vector2(),label=document.getElementById('label');
function renderInfo(){const d=info[selected]||info.robot;document.getElementById('title').textContent=d.title;document.getElementById('summary').textContent=d.summary;document.getElementById('kind').textContent=d.kind;document.getElementById('risk').textContent=d.risk;document.getElementById('detail').innerHTML='<h4>'+({overview:'你将看到',action:'如何操作',safety:'安全要点'}[tab])+'</h4><ul>'+d[tab].map(x=>'<li>'+x+'</li>').join('')+'</ul>'}renderInfo();
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.classList.remove('active'));b.classList.add('active');tab=b.dataset.tab;renderInfo()});
renderer.domElement.addEventListener('pointerdown',e=>{const r=renderer.domElement.getBoundingClientRect();mouse.x=(e.clientX-r.left)/r.width*2-1;mouse.y=-(e.clientY-r.top)/r.height*2+1;ray.setFromCamera(mouse,camera);const hit=ray.intersectObjects(clickable,true)[0];if(!hit)return;let o=hit.object;while(o&&!info[o.name])o=o.parent;if(o&&info[o.name]){selected=o.name;renderInfo();label.textContent=info[selected].title;label.style.display='block';label.style.left=(e.clientX-r.left)+'px';label.style.top=(e.clientY-r.top)+'px';setTimeout(()=>label.style.display='none',1500)}});
document.querySelectorAll('.task').forEach(b=>b.onclick=()=>{document.querySelectorAll('.task').forEach(x=>x.classList.remove('active'));b.classList.add('active');selected=b.dataset.target;renderInfo();setView(selected==='robot'?'robot':selected==='hazard'?'hazard':'overview')});
function resize(){const w=host.clientWidth,h=host.clientHeight;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h)}addEventListener('resize',resize);
const clock=new THREE.Clock();function loop(){requestAnimationFrame(loop);controls.update();const t=clock.getElapsedTime();hazard.material.opacity=.20+.045*(1+Math.sin(t*2.2));renderer.render(scene,camera)}loop();
</script>
</body>
</html>
"""
