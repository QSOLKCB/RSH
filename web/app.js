(() => {
  "use strict";

  const canvas = document.getElementById("helix");
  if (!(canvas instanceof HTMLCanvasElement)) return;
  const context = canvas.getContext("2d");
  if (!context) return;

  const points = Array.from({ length: 220 }, (_, index) => {
    const u = index / 219;
    const t = (u - 0.5) * Math.PI * 5.4;
    const envelope = 0.38 + 0.62 * Math.cos((u - 0.5) * Math.PI * 0.78);
    return {
      x: Math.cos(t) * envelope,
      y: (u - 0.5) * 2.6,
      z: Math.sin(t) * envelope,
      u,
    };
  });

  let pointerX = 0;
  let pointerY = 0;
  let phase = 0;

  function resize() {
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const box = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(box.width * ratio));
    canvas.height = Math.max(1, Math.floor(box.height * ratio));
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function rotate(point, yaw, pitch) {
    const cy = Math.cos(yaw);
    const sy = Math.sin(yaw);
    const cp = Math.cos(pitch);
    const sp = Math.sin(pitch);
    const x1 = point.x * cy - point.z * sy;
    const z1 = point.x * sy + point.z * cy;
    return {
      x: x1,
      y: point.y * cp - z1 * sp,
      z: point.y * sp + z1 * cp,
      u: point.u,
    };
  }

  function drawGrid(width, height) {
    context.save();
    context.strokeStyle = "rgba(145, 164, 170, 0.11)";
    context.lineWidth = 1;
    for (let x = 0; x <= width; x += 48) {
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, height);
      context.stroke();
    }
    for (let y = 0; y <= height; y += 48) {
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(width, y);
      context.stroke();
    }
    context.restore();
  }

  function render() {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    context.save();
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.restore();

    drawGrid(width, height);

    const yaw = phase * 0.22 + pointerX * 0.42;
    const pitch = -0.22 + pointerY * 0.23;
    const scale = Math.min(width, height) * 0.27;
    const projected = points.map((point) => {
      const rotated = rotate(point, yaw, pitch);
      const depth = 1.8 + rotated.z * 0.22;
      return {
        x: width * 0.5 + (rotated.x * scale) / depth,
        y: height * 0.5 + (rotated.y * scale) / depth,
        z: rotated.z,
        u: rotated.u,
      };
    });

    for (let layer = 0; layer < 2; layer += 1) {
      context.beginPath();
      projected.forEach((point, index) => {
        if (index === 0) context.moveTo(point.x, point.y);
        else context.lineTo(point.x, point.y);
      });
      context.lineJoin = "round";
      context.lineCap = "round";
      context.lineWidth = layer === 0 ? 12 : 2.3;
      context.strokeStyle = layer === 0
        ? "rgba(101, 217, 192, 0.075)"
        : "rgba(101, 217, 192, 0.88)";
      context.stroke();
    }

    projected.forEach((point, index) => {
      if (index % 8 !== 0) return;
      const alpha = 0.18 + ((point.z + 1) / 2) * 0.42;
      context.beginPath();
      context.arc(point.x, point.y, 1.5 + alpha * 1.5, 0, Math.PI * 2);
      context.fillStyle = `rgba(226, 166, 91, ${alpha})`;
      context.fill();
    });

    const centre = projected[Math.floor(projected.length / 2)];
    context.beginPath();
    context.arc(centre.x, centre.y, 20, 0, Math.PI * 2);
    context.strokeStyle = "rgba(232, 240, 241, 0.35)";
    context.lineWidth = 1;
    context.stroke();
    context.beginPath();
    context.arc(centre.x, centre.y, 4, 0, Math.PI * 2);
    context.fillStyle = "rgba(232, 240, 241, 0.96)";
    context.fill();

    phase += 0.004;
    requestAnimationFrame(render);
  }

  canvas.addEventListener("pointermove", (event) => {
    const box = canvas.getBoundingClientRect();
    pointerX = ((event.clientX - box.left) / box.width - 0.5) * 2;
    pointerY = ((event.clientY - box.top) / box.height - 0.5) * 2;
  });
  canvas.addEventListener("pointerleave", () => {
    pointerX = 0;
    pointerY = 0;
  });
  window.addEventListener("resize", resize);
  resize();
  render();
})();
