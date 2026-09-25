/**
 * Nostalgic sound effects, synthesized with the Web Audio API
 * rather than played from audio files - no assets to host, and these are
 * original tones we're generating in code, not recordings of any real
 * modem or a specific OS's chime. Who knew that was a thing? I didn't until Claude.
 */

let ctx;

function getContext() {
  if (!ctx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    ctx = new AudioContextClass();
  }
  if (ctx.state === "suspended") {
    ctx.resume();
  }
  return ctx;
}

function beep(context, freq, startTime, duration, gainPeak = 0.12) {
  const osc = context.createOscillator();
  const gain = context.createGain();
  osc.type = "square";
  osc.frequency.setValueAtTime(freq, startTime);
  gain.gain.setValueAtTime(0, startTime);
  gain.gain.linearRampToValueAtTime(gainPeak, startTime + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
  osc.connect(gain);
  gain.connect(context.destination);
  osc.start(startTime);
  osc.stop(startTime + duration);
}

// Approximation of a dial-up modem handshake
export function playDialUpSound() {
  try {
    const context = getContext();
    const now = context.currentTime;
    const freqs = [1200, 2100, 1400, 2400, 1800, 2600, 1500];
    const noteDuration = 0.26;
    const noteSpacing = 0.24; // slight overlap between notes, for a smoother warble
 
    freqs.forEach((freq, i) => {
      const start = now + i * noteSpacing;
      const osc = context.createOscillator();
      const gain = context.createGain();
      osc.type = "square";
      osc.frequency.setValueAtTime(freq, start);
      osc.frequency.linearRampToValueAtTime(freq * 0.85, start + noteDuration);
      gain.gain.setValueAtTime(0.05, start);
      gain.gain.exponentialRampToValueAtTime(0.001, start + noteDuration);
      osc.connect(gain);
      gain.connect(context.destination);
      osc.start(start);
      osc.stop(start + noteDuration);
    });
  } catch {
    // Web Audio can be unavailable or blocked in some environments - sound
    // is a nice-to-have and should never break the actual feature.
  }
}

/**
 * A simple two-tone descending beep, evoking the general idea of a
 * classic "something went wrong" computer chime without reproducing any
 * specific OS's actual sound file.
 */
export function playErrorSound() {
  try {
    const context = getContext();
    const now = context.currentTime;
    beep(context, 740, now, 0.18);
    beep(context, 440, now + 0.15, 0.28);
  } catch {
    // see note above
  }
}

function createNoiseBuffer(context, duration) {
  const length = Math.floor(context.sampleRate * duration);
  const buffer = context.createBuffer(1, length, context.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) {
    data[i] = Math.random() * 2 - 1;
  }
  return buffer;
}

/**
 * A theatrical thunderclap: a sharp high-frequency "crack" followed by a
 * longer low rumble that fades out. Built from filtered white noise
 * (randomly generated samples), not a recording of real thunder.
 */
export function playThunderClap() {
  try {
    const context = getContext();
    const now = context.currentTime;
 
    // The crack - a short burst of bright noise.
    const crackSource = context.createBufferSource();
    crackSource.buffer = createNoiseBuffer(context, 0.15);
    const crackFilter = context.createBiquadFilter();
    crackFilter.type = "highpass";
    crackFilter.frequency.value = 800;
    const crackGain = context.createGain();
    crackGain.gain.setValueAtTime(0.3, now);
    crackGain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
    crackSource.connect(crackFilter);
    crackFilter.connect(crackGain);
    crackGain.connect(context.destination);
    crackSource.start(now);
    crackSource.stop(now + 0.15);
 
    // The rumble - heavily low-passed noise, decaying over ~1.8s.
    const rumbleSource = context.createBufferSource();
    rumbleSource.buffer = createNoiseBuffer(context, 1.8);
    const rumbleFilter = context.createBiquadFilter();
    rumbleFilter.type = "lowpass";
    rumbleFilter.frequency.setValueAtTime(450, now);
    rumbleFilter.frequency.exponentialRampToValueAtTime(70, now + 1.8);
    const rumbleGain = context.createGain();
    rumbleGain.gain.setValueAtTime(0, now);
    rumbleGain.gain.linearRampToValueAtTime(0.4, now + 0.06);
    rumbleGain.gain.exponentialRampToValueAtTime(0.001, now + 1.8);
    rumbleSource.connect(rumbleFilter);
    rumbleFilter.connect(rumbleGain);
    rumbleGain.connect(context.destination);
    rumbleSource.start(now);
    rumbleSource.stop(now + 1.8);
  } catch {
    // see note above
  }
}