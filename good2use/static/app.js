const img = document.getElementById('cam');
const statusEl = document.getElementById('status');
const logEl = document.getElementById('log');
const dataEl = document.getElementById('data');
const bees = document.getElementById('txt-box');
const flws = document.getElementById('flowers');
const date = document.getElementById('date');
let state = false;
let debug = false;
let coords = "";
let scale= 10;
let hover = false;

function log(s) {
  logEl.textContent = (new Date().toLocaleTimeString() + "  " + s + "\n") + logEl.textContent;
}

function setRunning(running) {
  if (running) {
    img.src = "/mjpeg";
    statusEl.textContent = "статус: запущено (mjpeg)";
  } else {
    img.src = "/frame.jpg?t=" + Date.now();
    statusEl.textContent = "статус: остановлено (зафиксирован последний кадр)";
  }
}

const wsProto = (location.protocol === "https:") ? "wss" : "ws";
const ws = new WebSocket(`${wsProto}://${location.host}/ws`);

ws.onopen = () => log("WS connected");
ws.onclose = () => log("WS closed");
ws.onerror = () => log("WS error");

ws.onmessage = (ev) => {
  
  try {
    
    const data = JSON.parse(ev.data);
    console.log(data.type);
    if (data.type == "robstate") {
      bees.textContent = data.state;
    }
    if (data.type == "state") {
      log("WS <- " + ev.data);
      setRunning(data.streaming);
    }
    else if (data.type == "coordinates"){
      log("WS <- " + ev.data);
    }
    else if (data.type == "robstate"){
      bees.textContent += ev.data
    }
  } catch {}
};

function send(obj) {
  const s = JSON.stringify(obj);
  ws.send(s);
  
    log("WS -> " + s);   
  
  
}
const intervalId = setInterval(() => { 
  send({type:"robstate",id:""})
  date.textContent = new Date().toLocaleTimeString();
}, 1000)
function Hover() {
  
    hover = true;

}
function NHover() {

    hover = false;
   
}

  
document.addEventListener('wheel', function(event) {  
    // Получаем значение величины прокрутки колеса мыши    
    if(hover) {    
      scale -= event.deltaY/20;
      if (scale<=10) {
        scale=10;
      }
      else if (scale>=100) {
        scale=100;
      }           
    send({type:"zoom", value:scale});
    }
    
});



function onChangeState() {
  
  state=!state;
  let div = document.querySelector("#cam");
  let chng = document.getElementById("change_state");
  const rect = div.getBoundingClientRect();  

  if(state) {
      chng.style.color = 'black';
      chng.style.background = 'white';
    }
    else {
      chng.style.color = 'white';
      chng.style.background = 'black';
    }
   div.addEventListener('click', (e) => {
    let x = e.pageX,
    y = e.pageY;
    
  // console.log(`${x - div.offsetLeft+(Math.round(rect.width/2))}:${y-div.offsetTop+(Math.round(rect.height/2))}`);
    
      coords=`(${x - div.offsetLeft+(Math.round(rect.width/2))};${y-div.offsetTop+(Math.round(rect.height/2))})`        
    
    
  }, {
  capture: true
})
  
  
    
  }
function onDebug() {
  debug=!debug;
  let deb = document.getElementById("col_deb");
  if(debug) {
    deb.style.color = 'black';
    deb.style.background = 'white';
  }
  else {
    deb.style.color = 'white';
    deb.style.background = 'black';
  }
}

function onCamClick() {
  if(state) {
    send({type:"coordinates",coordinates:coords})
  }
}
  

  

  


document.getElementById('start').onclick = () => send({type:"start"});
document.getElementById('stop').onclick  = () => send({type:"stop"});

setRunning(true);