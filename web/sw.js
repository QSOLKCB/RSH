const CACHE_NAME = "rsh-browser-lab-v2.7.0-parallel-v1";
const CORE_ASSETS = [
  "./",
  "./index.html",
  "./style.css",
  "./gpu.css",
  "./app.js",
  "./gpu.js",
  "./frenet.html",
  "./frenet.css",
  "./frenet.js",
  "./path-gpu.js",
  "./parallel.html",
  "./parallel.css",
  "./parallel.js",
  "./parallel-gpu.js",
  "./tissue.html",
  "./tissue.css",
  "./tissue.js",
  "./wgsl/kappa_tau_field.wgsl",
  "./wgsl/frenet_path.wgsl",
  "./wgsl/frenet_parallel_scan.wgsl",
  "./pkg/rsh_wasm.wasm",
  "./pkg/rsh_numerics_wasm.wasm",
  "./pkg/rsh_parallel_wasm.wasm",
  "./pkg/rsh_tissue_wasm.wasm",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(CORE_ASSETS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names
          .filter((name) => name.startsWith("rsh-browser-lab-") && name !== CACHE_NAME)
          .map((name) => caches.delete(name)),
      ))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) return;

  const revalidation = fetch(event.request).then(async (response) => {
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(event.request, response.clone());
    }
    return response;
  });

  event.waitUntil(revalidation.then(() => undefined).catch(() => undefined));
  event.respondWith(caches.match(event.request).then((cached) => cached || revalidation));
});
