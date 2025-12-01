import { Buffer } from 'buffer';

// Polyfill global
if (typeof window !== 'undefined') {
  window.global = window;
}

// Polyfill Buffer
globalThis.Buffer = Buffer;

// Polyfill process
if (typeof window !== 'undefined' && !window.process) {
  // @ts-ignore
  window.process = {
    env: { NODE_ENV: import.meta.env.MODE },
    version: '',
    nextTick: (fn: Function) => setTimeout(fn, 0),
    platform: 'browser',
  };
}

console.log("Polyfills loaded successfully");
