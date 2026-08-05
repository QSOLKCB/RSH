#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const EXIT_ARGUMENT = 2;
const EXIT_ENVIRONMENT = 20;
const EXIT_SCHEDULE = 31;
const EXIT_PARALLEL = 32;

function parseArguments(argv) {
  const options = {
    baseUrl: "http://127.0.0.1:8765/",
    output: "artifacts/rtx-hardware/webgpu",
    chrome: process.env.CHROME_BIN || "/usr/bin/google-chrome-stable",
    mode: "graphical",
    timeout: 180_000,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    const value = () => {
      index += 1;
      if (index >= argv.length) throw new Error(`${argument} requires a value`);
      return argv[index];
    };
    switch (argument) {
      case "--base-url": options.baseUrl = value(); break;
      case "--output": options.output = value(); break;
      case "--chrome": options.chrome = value(); break;
      case "--mode": options.mode = value(); break;
      case "--timeout": options.timeout = Number(value()); break;
      case "--help":
      case "-h":
        console.log(`Usage: test_rtx_webgpu.cjs [options]\n\n  --base-url URL       local secure-context URL (default http://127.0.0.1:8765/)\n  --output DIR         empty evidence directory\n  --chrome PATH        Chrome executable\n  --mode MODE          graphical or headless\n  --timeout MS         per-surface timeout\n`);
        process.exit(0);
      default: throw new Error(`unknown argument: ${argument}`);
    }
  }
  if (!/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(options.baseUrl)) {
    throw new Error("--base-url must use localhost or 127.0.0.1");
  }
  if (!options.baseUrl.endsWith("/")) options.baseUrl += "/";
  if (!["graphical", "headless"].includes(options.mode)) {
    throw new Error("--mode must be graphical or headless");
  }
  if (!Number.isSafeInteger(options.timeout) || options.timeout < 30_000 || options.timeout > 600_000) {
    throw new Error("--timeout must be an integer in [30000, 600000]");
  }
  return options;
}

function prepareOutput(directory) {
  const resolved = path.resolve(directory);
  if (fs.existsSync(resolved)) {
    if (!fs.statSync(resolved).isDirectory()) throw new Error(`output is not a directory: ${resolved}`);
    if (fs.readdirSync(resolved).length !== 0) throw new Error(`output directory must be empty: ${resolved}`);
  } else {
    fs.mkdirSync(resolved, { recursive: true });
  }
  return resolved;
}

function writeJson(file, payload) {
  fs.writeFileSync(file, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function finite(value, name) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) throw new Error(`${name} is not finite`);
  return numeric;
}

function requireBoolean(value, expected, name) {
  if (value !== expected) throw new Error(`${name} must be ${expected}`);
}

function validatePhysicalAdapter(text) {
  const adapter = String(text || "").trim();
  const lowered = adapter.toLowerCase();
  if (!adapter) throw new Error("WebGPU adapter metadata is empty");
  if (!lowered.includes("nvidia")) throw new Error(`expected an NVIDIA adapter, received: ${adapter}`);
  if (/swiftshader|llvmpipe|software|lavapipe/.test(lowered)) {
    throw new Error(`software WebGPU adapter is not accepted: ${adapter}`);
  }
  return adapter;
}

async function installBlobCapture(page) {
  await page.evaluateOnNewDocument(() => {
    globalThis.__rshCapturedDownload = null;
    const originalCreateObjectURL = URL.createObjectURL.bind(URL);
    URL.createObjectURL = (blob) => {
      if (blob instanceof Blob) {
        blob.text().then((text) => {
          globalThis.__rshCapturedDownload = {
            text,
            type: blob.type,
            captured_at: new Date().toISOString(),
          };
        }).catch((error) => {
          globalThis.__rshCapturedDownload = { error: String(error) };
        });
      }
      return originalCreateObjectURL(blob);
    };
  });
}

async function capturedJson(page, buttonSelector, timeout) {
  await page.evaluate(() => { globalThis.__rshCapturedDownload = null; });
  await page.click(buttonSelector);
  await page.waitForFunction(
    () => globalThis.__rshCapturedDownload !== null,
    { timeout },
  );
  const captured = await page.evaluate(() => globalThis.__rshCapturedDownload);
  if (captured?.error) throw new Error(`download capture failed: ${captured.error}`);
  if (!captured?.text) throw new Error("download capture returned no text");
  const payload = JSON.parse(captured.text);
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("captured download is not a JSON object");
  }
  return payload;
}

async function pageSnapshot(page, selectors) {
  return page.evaluate((requested) => Object.fromEntries(
    requested.map((selector) => [
      selector,
      document.querySelector(selector)?.textContent?.trim() ?? null,
    ]),
  ), selectors);
}

function validateScheduleSidecar(sidecar) {
  if (sidecar.schema !== "RSH-WEBGPU-RESIDUAL-SIDECAR-V1") {
    throw new Error(`unexpected schedule sidecar schema: ${sidecar.schema}`);
  }
  requireBoolean(sidecar.residual_gate_passed, true, "schedule residual_gate_passed");
  requireBoolean(sidecar.visual_verified, false, "schedule visual_verified");
  const adapter = validatePhysicalAdapter(sidecar.metadata?.adapter);
  const maximum = finite(sidecar.residuals?.residual_max_vs_cpu, "schedule maximum residual");
  const threshold = finite(sidecar.residuals?.threshold, "schedule threshold");
  if (maximum > threshold) throw new Error(`schedule residual ${maximum} exceeds ${threshold}`);
  return { adapter, maximum, threshold };
}

function validateParallelSidecar(sidecar) {
  if (sidecar.schema !== "RSH-WEBGPU-FRENET-PARALLEL-BENCHMARK-V1") {
    throw new Error(`unexpected parallel sidecar schema: ${sidecar.schema}`);
  }
  if (sidecar.status !== "PASS") throw new Error(`parallel sidecar status is ${sidecar.status}`);
  requireBoolean(sidecar.actual_gpu_execution, true, "parallel actual_gpu_execution");
  requireBoolean(sidecar.parallel_scan_execution, true, "parallel parallel_scan_execution");
  requireBoolean(sidecar.complete_path_readback, true, "parallel complete_path_readback");
  requireBoolean(sidecar.actual_multi_device_execution, false, "parallel actual_multi_device_execution");
  requireBoolean(sidecar.distributed_execution, false, "parallel distributed_execution");
  requireBoolean(sidecar.universal_speedup_claim, false, "parallel universal_speedup_claim");
  requireBoolean(sidecar.geometry_receipt_authority, false, "parallel geometry_receipt_authority");
  const adapter = validatePhysicalAdapter(sidecar.metadata?.adapter);
  if (sidecar.configuration?.samples !== 4097) throw new Error("parallel sample count must be 4097");
  if (sidecar.metadata?.scan_passes !== 13) throw new Error("parallel scan pass count must be 13");
  if (sidecar.metadata?.transform_bytes !== 32) throw new Error("parallel transform size must be 32 bytes");
  if (sidecar.benchmark?.warmup_runs !== 2 || sidecar.benchmark?.measured_runs !== 7) {
    throw new Error("parallel benchmark must retain two warm-ups and seven measured runs");
  }
  const residuals = sidecar.residuals || {};
  const gates = sidecar.gates || {};
  const comparisons = [
    ["max_position_component_vs_f64", "position_component_gate"],
    ["max_frame_component_vs_f64", "frame_component_gate"],
    ["max_schedule_component_vs_f64", "schedule_component_gate"],
    ["max_frame_norm_error", "frame_norm_gate"],
    ["max_frame_orthogonality_error", "frame_orthogonality_gate"],
  ];
  for (const [residualName, gateName] of comparisons) {
    const residual = finite(residuals[residualName], `parallel ${residualName}`);
    const gate = finite(gates[gateName], `parallel ${gateName}`);
    if (residual > gate) throw new Error(`${residualName} ${residual} exceeds ${gate}`);
  }
  return { adapter };
}

async function testSchedule(browser, options, consoleLog) {
  const page = await browser.newPage();
  await installBlobCapture(page);
  page.on("console", (message) => consoleLog.push(`[schedule:${message.type()}] ${message.text()}`));
  page.on("pageerror", (error) => consoleLog.push(`[schedule:pageerror] ${error.stack || error}`));
  await page.goto(options.baseUrl, { waitUntil: "networkidle0", timeout: options.timeout });
  await page.waitForFunction(
    () => document.querySelector("#runtime-status")?.textContent?.toLowerCase().includes("ready"),
    { timeout: options.timeout },
  );
  await page.click("#run-button");
  await page.waitForFunction(
    () => ["RESIDUAL PASS", "DISPLAY ONLY", "CPU/WASM FALLBACK"].includes(
      document.querySelector("#gpu-status")?.textContent?.trim(),
    ),
    { timeout: options.timeout },
  );
  const snapshot = await pageSnapshot(page, [
    "#gpu-status", "#gpu-message", "#gpu-adapter", "#gpu-grid", "#gpu-workgroup",
    "#gpu-kappa-residual", "#gpu-tau-residual", "#gpu-max-residual", "#gpu-gate",
  ]);
  const status = snapshot["#gpu-status"];
  if (status !== "RESIDUAL PASS") {
    const evidence = {
      schema: "RSH-TRUSTED-RTX-WEBGPU-SCHEDULE-V1",
      status: status === "DISPLAY ONLY" ? "REJECTED" : "BLOCKED BY ENVIRONMENT",
      observed: snapshot,
      actual_gpu_execution: status === "DISPLAY ONLY",
      complete_field_readback: status === "DISPLAY ONLY",
      speedup_claim: false,
      universal_speedup_claim: false,
      geometry_receipt_authority: false,
    };
    await page.close();
    return { pass: false, evidence };
  }
  const sidecar = await capturedJson(page, "#download-gpu", options.timeout);
  const validation = validateScheduleSidecar(sidecar);
  const evidence = {
    schema: "RSH-TRUSTED-RTX-WEBGPU-SCHEDULE-V1",
    status: "PASS",
    source_sidecar: sidecar,
    adapter: validation.adapter,
    maximum_residual: validation.maximum,
    threshold: validation.threshold,
    actual_gpu_execution: true,
    complete_field_readback: true,
    speedup_claim: false,
    universal_speedup_claim: false,
    geometry_receipt_authority: false,
  };
  await page.close();
  return { pass: true, evidence };
}

async function testParallel(browser, options, consoleLog) {
  const page = await browser.newPage();
  await installBlobCapture(page);
  page.on("console", (message) => consoleLog.push(`[parallel:${message.type()}] ${message.text()}`));
  page.on("pageerror", (error) => consoleLog.push(`[parallel:pageerror] ${error.stack || error}`));
  await page.goto(`${options.baseUrl}parallel.html`, { waitUntil: "networkidle0", timeout: options.timeout });
  await page.waitForFunction(
    () => document.querySelector("#status")?.textContent?.trim() === "READY",
    { timeout: options.timeout },
  );
  await page.select("#samples", "4097");
  await page.click("#run");
  await page.waitForFunction(
    () => ["PARALLEL PATH PASS", "REJECTED", "WASM FALLBACK", "DEVICE LOST"].includes(
      document.querySelector("#status")?.textContent?.trim(),
    ),
    { timeout: options.timeout },
  );
  const snapshot = await pageSnapshot(page, [
    "#status", "#message", "#adapter", "#scan-passes", "#res-position", "#res-frame",
    "#res-schedule", "#res-norm", "#res-orthogonality", "#wasm-median", "#gpu-median",
    "#speedup", "#claim",
  ]);
  const status = snapshot["#status"];
  let sidecar = null;
  const downloadEnabled = await page.$eval("#download", (button) => !button.disabled);
  if (downloadEnabled) sidecar = await capturedJson(page, "#download", options.timeout);
  if (status !== "PARALLEL PATH PASS") {
    const evidence = sidecar || {
      schema: "RSH-TRUSTED-RTX-WEBGPU-PARALLEL-V1",
      status: status === "REJECTED" ? "REJECTED" : "BLOCKED BY ENVIRONMENT",
      observed: snapshot,
      actual_gpu_execution: status === "REJECTED",
      parallel_scan_execution: status === "REJECTED",
      complete_path_readback: status === "REJECTED",
      actual_multi_device_execution: false,
      distributed_execution: false,
      speedup_claim: false,
      universal_speedup_claim: false,
      geometry_receipt_authority: false,
    };
    await page.close();
    return { pass: false, evidence };
  }
  if (!sidecar) throw new Error("parallel pass did not produce an evidence sidecar");
  validateParallelSidecar(sidecar);
  await page.close();
  return { pass: true, evidence: sidecar };
}

async function main() {
  let options;
  try {
    options = parseArguments(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    return EXIT_ARGUMENT;
  }

  let output;
  try {
    output = prepareOutput(options.output);
  } catch (error) {
    console.error(error.message);
    return EXIT_ARGUMENT;
  }
  if (!fs.existsSync(options.chrome)) {
    console.error(`Chrome executable not found: ${options.chrome}`);
    return EXIT_ENVIRONMENT;
  }

  let puppeteer;
  try {
    puppeteer = require("puppeteer-core");
  } catch (error) {
    console.error(`puppeteer-core is unavailable: ${error.message}`);
    return EXIT_ENVIRONMENT;
  }

  const args = [
    "--use-angle=vulkan",
    "--enable-features=Vulkan",
    "--enable-unsafe-webgpu",
    "--ignore-gpu-blocklist",
    "--disable-software-rasterizer",
    "--disable-dev-shm-usage",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
  ];
  if (options.mode === "headless") {
    args.push("--headless=new", "--disable-vulkan-surface");
  } else if (process.env.WAYLAND_DISPLAY) {
    args.push("--ozone-platform=wayland");
  } else if (process.env.DISPLAY) {
    args.push("--ozone-platform=x11");
  } else {
    console.error("graphical mode requires WAYLAND_DISPLAY or DISPLAY");
    return EXIT_ENVIRONMENT;
  }
  if (typeof process.getuid === "function" && process.getuid() === 0) args.push("--no-sandbox");

  const consoleLog = [];
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: options.chrome,
      headless: options.mode === "headless" ? "new" : false,
      args,
    });
    const browserVersion = await browser.version();
    const schedule = await testSchedule(browser, options, consoleLog);
    writeJson(path.join(output, "schedule.json"), schedule.evidence);
    const parallel = await testParallel(browser, options, consoleLog);
    writeJson(path.join(output, "parallel.json"), parallel.evidence);
    const summary = {
      schema: "RSH-TRUSTED-RTX-WEBGPU-RESULT-V1",
      status: schedule.pass && parallel.pass ? "PASS" : "FAIL",
      browser: browserVersion,
      mode: options.mode,
      base_url: options.baseUrl,
      schedule_status: schedule.evidence.status,
      parallel_status: parallel.evidence.status,
      actual_schedule_gpu_execution: schedule.evidence.actual_gpu_execution === true,
      actual_parallel_gpu_execution: parallel.evidence.actual_gpu_execution === true,
      complete_schedule_readback: schedule.evidence.complete_field_readback === true,
      complete_parallel_readback: parallel.evidence.complete_path_readback === true,
      universal_speedup_claim: false,
      geometry_receipt_authority: false,
    };
    writeJson(path.join(output, "audit-summary.json"), summary);
    fs.writeFileSync(path.join(output, "browser-console.txt"), `${consoleLog.join("\n")}\n`, "utf8");
    console.log(JSON.stringify(summary, null, 2));
    if (!schedule.pass) return EXIT_SCHEDULE;
    if (!parallel.pass) return EXIT_PARALLEL;
    return 0;
  } catch (error) {
    const summary = {
      schema: "RSH-TRUSTED-RTX-WEBGPU-RESULT-V1",
      status: "BLOCKED BY ENVIRONMENT",
      failure: error instanceof Error ? error.message : String(error),
      mode: options.mode,
      universal_speedup_claim: false,
      geometry_receipt_authority: false,
    };
    writeJson(path.join(output, "audit-summary.json"), summary);
    fs.writeFileSync(path.join(output, "browser-console.txt"), `${consoleLog.join("\n")}\n`, "utf8");
    console.error(summary.failure);
    return EXIT_ENVIRONMENT;
  } finally {
    if (browser) await browser.close();
  }
}

main().then((code) => { process.exitCode = code; }).catch((error) => {
  console.error(error);
  process.exitCode = EXIT_ENVIRONMENT;
});
