const img = document.getElementById('cam');
const statusEl = document.getElementById('status');
const logEl = document.getElementById('log');

function log(s) {
  logEl.textContent = (new Date().toLocaleTimeString() + "  " + s + "\n") + logEl.textContent;
}

function setRunning(running) {
  if (running) {
    img.src = "/mjpeg";
    statusEl.textContent = "status: running (mjpeg)";
  } else {
    img.src = "/frame.jpg?t=" + Date.now();
    statusEl.textContent = "status: stopped (frozen last frame)";
  }
}

const wsProto = (location.protocol === "https:") ? "wss" : "ws";
const ws = new WebSocket(`${wsProto}://${location.host}/ws`);

ws.onopen = () => log("WS connected");
ws.onclose = () => log("WS closed");
ws.onerror = () => log("WS error");

ws.onmessage = (ev) => {
  log("WS <- " + ev.data);
  try {
    const data = JSON.parse(ev.data);
    if (data.type === "state") setRunning(data.streaming);
  } catch {}
};

function send(obj) {
  const s = JSON.stringify(obj);
  ws.send(s);
  log("WS -> " + s);
}

document.getElementById('start').onclick = () => send({type:"start"});
document.getElementById('stop').onclick  = () => send({type:"stop"});

setRunning(true);