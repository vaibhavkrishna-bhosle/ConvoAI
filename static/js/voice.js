// Voice: microphone recording (sent to the local Whisper endpoint) and read-aloud with
// voices installed on this computer. Nothing here talks to an online speech service.

const SILENCE_LEVEL = 0.018;   // RMS below this counts as silence
const END_SILENCE_MS = 1500;   // stop this long after the speaker goes quiet
const NO_SPEECH_MS = 8000;     // give up if nothing is said at all
const MAX_MS = 30000;          // hard limit per question

export const micSupported = () => !!(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);

function pickMime() {
  const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
  return types.find((t) => MediaRecorder.isTypeSupported?.(t)) || '';
}

/**
 * One recording. Call start(); it resolves with a Blob when recording ends
 * (silence, max length, or stop()), or with null if cancelled / nothing was said.
 * onLevel(0..1, elapsedMs) is called ~30x per second for the level meter.
 */
export class Recorder {
  constructor({ onLevel } = {}) {
    this.onLevel = onLevel;
    this.cancelled = false;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
    });
    const mimeType = pickMime();
    this.recorder = new MediaRecorder(this.stream, mimeType ? { mimeType, audioBitsPerSecond: 48000 } : undefined);
    const chunks = [];
    this.recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };

    // Level meter + silence detection
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    const source = this.ctx.createMediaStreamSource(this.stream);
    const analyser = this.ctx.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);
    const buf = new Float32Array(analyser.fftSize);

    const started = performance.now();
    let heardSpeech = false;
    let lastLoud = started;

    const done = new Promise((resolve) => {
      this.recorder.onstop = () => {
        this._release();
        if (!heardSpeech && !this.cancelled) this.cancelReason = 'silence';
        resolve(this.cancelled || !heardSpeech || !chunks.length ? null : new Blob(chunks, { type: this.recorder.mimeType || 'audio/webm' }));
      };
    });

    const tick = () => {
      if (this.recorder.state !== 'recording') return;
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += v * v;
      const rms = Math.sqrt(sum / buf.length);
      const now = performance.now();
      if (rms > SILENCE_LEVEL) { lastLoud = now; heardSpeech = true; }
      this.onLevel?.(Math.min(1, rms * 8), now - started);
      if ((heardSpeech && now - lastLoud > END_SILENCE_MS) || now - started > MAX_MS) { this.stop(); return; }
      if (!heardSpeech && now - started > NO_SPEECH_MS) { this.cancel('silence'); }
    };

    this.recorder.start(250);
    // A timer, not requestAnimationFrame: rAF pauses in background tabs, which would stop
    // silence detection (and the 30 s limit) if the user switched tabs mid-question.
    this.timer = setInterval(tick, 50);
    return done;
  }

  stop() {
    if (this.recorder?.state === 'recording') this.recorder.stop();
  }

  /** reason: 'user' (Esc / cancel) or 'silence' (nothing was said). */
  cancel(reason = 'user') {
    this.cancelled = true;
    this.cancelReason = reason;
    this.stop();
  }

  _release() {
    clearInterval(this.timer);
    this.stream?.getTracks().forEach((t) => t.stop());
    this.ctx?.close().catch(() => {});
  }
}

// ------------------------------------------------------------------ read aloud
export const ttsSupported = () => 'speechSynthesis' in window;

let voicesReady = null;
function loadVoices() {
  if (!voicesReady) {
    voicesReady = new Promise((resolve) => {
      const got = () => { const v = speechSynthesis.getVoices(); if (v.length) resolve(v); };
      got();
      speechSynthesis.addEventListener('voiceschanged', got);
      setTimeout(() => resolve(speechSynthesis.getVoices()), 1500);
    });
  }
  return voicesReady;
}

/** Only voices installed on this computer (localService); online voices would send the text away. */
export async function localVoice() {
  const voices = (await loadVoices()).filter((v) => v.localService);
  return voices.find((v) => v.lang === 'en-IN')
    || voices.find((v) => v.lang === 'en-GB')
    || voices.find((v) => v.lang?.startsWith('en'))
    || null;
}

/** Turn a Markdown answer with [1] citations into plain sentences for speaking. */
export function speechText(markdown) {
  return markdown
    .replace(/\s*\[\d{1,2}\]/g, '')                 // citations
    .replace(/```[\s\S]*?```/g, ' ')               // code blocks
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')        // links → text
    .replace(/^\s*\|?[-:| ]{3,}\|?\s*$/gm, '')       // table rules
    .replace(/\|/g, ', ')                           // table cells
    .replace(/^\s*[-*+]\s+/gm, '')                  // bullets
    .replace(/^\s*\d+\.\s+/gm, '')                  // numbered steps
    .replace(/[*_`#>]/g, '')                        // emphasis, headings, quotes
    .replace(/_\(Stopped\.\)_|\(Stopped\.\)/g, '')
    .replace(/\s*\n+\s*/g, '. ')
    .replace(/\.\s*\./g, '.')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

let speakingId = null;

export function isSpeaking(id) { return speakingId === id && speechSynthesis.speaking; }

export function stopSpeaking() {
  speakingId = null;
  if (ttsSupported()) speechSynthesis.cancel();
}

/** Speak an answer sentence by sentence (long single utterances get cut off in Chromium). */
export async function speak(id, markdown, { onEnd } = {}) {
  if (!ttsSupported()) return false;
  stopSpeaking();
  const voice = await localVoice();
  if (!voice) return false;
  speakingId = id;
  const sentences = speechText(markdown).match(/[^.!?]+[.!?]*/g) || [];
  sentences.forEach((s, i) => {
    const u = new SpeechSynthesisUtterance(s.trim());
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = 1.02;
    if (i === sentences.length - 1) u.onend = () => { if (speakingId === id) { speakingId = null; onEnd?.(); } };
    speechSynthesis.speak(u);
  });
  return true;
}
