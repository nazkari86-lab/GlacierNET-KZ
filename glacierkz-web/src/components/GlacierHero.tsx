"use client";

import { useEffect, useState } from "react";
import { ArrowDown } from "lucide-react";

const FACTS = [
  "Since 1950, Kazakhstan's glaciers have lost over 40% of their area.",
  "By 2050, most glaciers in the Zailiysky Alatau may disappear entirely.",
  "Glacier melt threatens water supply for 6 million people in Central Asia.",
  "The Tuyuksu glacier has receded more than 1 km in the last 60 years.",
];

export default function GlacierHero() {
  const [factIndex, setFactIndex] = useState(0);
  const [showStat, setShowStat] = useState(false);
  const [mounted, setMounted] = useState(false);

  const [particles, setParticles] = useState<
    { left: number; delay: number; duration: number; opacity: number; size: number }[]
  >([]);
  const [stars, setStars] = useState<
    { cx: number; cy: number; opacity: number; delay: number }[]
  >([]);

  useEffect(() => {
    setMounted(true);
    setParticles(
      Array.from({ length: 30 }, () => ({
        left: Math.random() * 100,
        delay: Math.random() * 8,
        duration: 6 + Math.random() * 6,
        opacity: 0.2 + Math.random() * 0.5,
        size: 2 + Math.random() * 3,
      }))
    );
    setStars(
      Array.from({ length: 40 }, () => ({
        cx: Math.random() * 1200,
        cy: Math.random() * 150,
        opacity: 0.3 + Math.random() * 0.5,
        delay: Math.random() * 3,
      }))
    );
    const t1 = setTimeout(() => setShowStat(true), 2500);
    const t2 = setInterval(() => {
      setFactIndex((i) => (i + 1) % FACTS.length);
    }, 4000);
    return () => {
      clearTimeout(t1);
      clearInterval(t2);
    };
  }, []);

  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-sky-950 via-blue-900 to-blue-800">
      {/* Ice particles */}
      {mounted && (
        <div className="pointer-events-none absolute inset-0">
          {particles.map((p, i) => (
            <div
              key={i}
              className="absolute rounded-full bg-white/40"
              style={{
                left: `${p.left}%`,
                animation: `float-up ${p.duration}s linear infinite`,
                animationDelay: `${p.delay}s`,
                opacity: p.opacity,
                width: `${p.size}px`,
                height: `${p.size}px`,
              }}
            />
          ))}
        </div>
      )}

      {/* Glacier SVG */}
      <div className="pointer-events-none absolute bottom-0 w-full">
        <svg viewBox="0 0 1200 400" className="h-auto w-full" preserveAspectRatio="xMidYMax meet">
          <defs>
            <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#075985" />
              <stop offset="100%" stopColor="#1e40af" />
            </linearGradient>
            <linearGradient id="ice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#bae6fd" />
              <stop offset="100%" stopColor="#7dd3fc" />
            </linearGradient>
            <linearGradient id="snow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="100%" stopColor="#e0f2fe" />
            </linearGradient>
            <linearGradient id="rock" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#475569" />
              <stop offset="100%" stopColor="#334155" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background sky */}
          <rect width="1200" height="400" fill="url(#sky)" />

          {/* Stars (only render after mount to avoid hydration mismatch) */}
          {mounted &&
            stars.map((s, i) => (
              <circle
                key={i}
                cx={s.cx}
                cy={s.cy}
                r={1}
                fill="white"
                opacity={s.opacity}
                className="animate-pulse"
                style={{ animationDelay: `${s.delay}s` }}
              />
            ))}

          {/* Moon */}
          <circle cx="950" cy="80" r="35" fill="#f0f9ff" opacity="0.8" filter="url(#glow)" />
          <circle cx="960" cy="75" r="30" fill="#075985" opacity="0.6" />

          {/* Far mountain range */}
          <path d="M0 250 Q100 180 200 220 Q300 160 400 200 Q500 140 600 190 Q700 130 800 180 Q900 120 1000 170 Q1100 140 1200 200 L1200 400 L0 400Z" fill="#1e3a5f" opacity="0.5" />

          {/* Mountain range with ice caps */}
          <path d="M0 280 L80 200 L150 240 L220 160 L300 220 L350 180 L420 120 L500 190 L560 150 L640 100 L720 170 L800 130 L880 190 L960 140 L1040 200 L1120 160 L1200 230 L1200 400 L0 400Z" fill="url(#rock)" />

          {/* Ice caps on mountains - animated */}
          <g filter="url(#glow)">
            <path className="animate-melt" d="M220 160 L250 185 L190 185Z" fill="url(#ice)" style={{ animationDelay: "0s" }} />
            <path className="animate-melt" d="M420 120 L455 150 L385 150Z" fill="url(#ice)" style={{ animationDelay: "0.5s" }} />
            <path className="animate-melt" d="M640 100 L678 135 L602 135Z" fill="url(#ice)" style={{ animationDelay: "1s" }} />
            <path className="animate-melt" d="M800 130 L835 160 L765 160Z" fill="url(#ice)" style={{ animationDelay: "1.5s" }} />
            <path className="animate-melt" d="M960 140 L992 168 L928 168Z" fill="url(#ice)" style={{ animationDelay: "2s" }} />
            <path className="animate-melt" d="M1120 160 L1148 185 L1092 185Z" fill="url(#ice)" style={{ animationDelay: "2.5s" }} />
          </g>

          {/* Snow caps */}
          <g>
            <path d="M220 160 L240 175 L200 175Z" fill="url(#snow)" opacity="0.6" />
            <path d="M420 120 L442 138 L398 138Z" fill="url(#snow)" opacity="0.6" />
            <path d="M640 100 L665 120 L615 120Z" fill="url(#snow)" opacity="0.6" />
            <path d="M800 130 L822 148 L778 148Z" fill="url(#snow)" opacity="0.6" />
            <path d="M960 140 L980 156 L940 156Z" fill="url(#snow)" opacity="0.6" />
            <path d="M1120 160 L1138 175 L1102 175Z" fill="url(#snow)" opacity="0.6" />
          </g>

          {/* Glacier front / ice flow */}
          <path className="animate-glacier" d="M580 180 Q620 200 660 190 Q700 210 750 200 Q780 220 820 210 L800 240 L600 240Z" fill="#7dd3fc" opacity="0.4">
            <animate attributeName="d" dur="4s" repeatCount="indefinite"
              values="M580 180 Q620 200 660 190 Q700 210 750 200 Q780 220 820 210 L800 240 L600 240Z;
                      M580 185 Q620 205 660 195 Q700 215 750 205 Q780 225 820 215 L800 245 L600 245Z;
                      M580 180 Q620 200 660 190 Q700 210 750 200 Q780 220 820 210 L800 240 L600 240Z" />
          </path>

          {/* Water surface */}
          <path d="M0 350 Q200 340 400 350 Q600 360 800 345 Q1000 335 1200 350 L1200 400 L0 400Z" fill="#0369a1" opacity="0.4">
            <animate attributeName="d" dur="3s" repeatCount="indefinite"
              values="M0 350 Q200 340 400 350 Q600 360 800 345 Q1000 335 1200 350 L1200 400 L0 400Z;
                      M0 352 Q200 345 400 352 Q600 358 800 348 Q1000 338 1200 352 L1200 400 L0 400Z;
                      M0 350 Q200 340 400 350 Q600 360 800 345 Q1000 335 1200 350 L1200 400 L0 400Z" />
          </path>
        </svg>
      </div>

      {/* Text content */}
      <div className="relative z-10 mx-auto max-w-4xl px-4 text-center">
        <div className="mb-6">
          <span className="inline-block animate-fadeIn rounded-full bg-white/10 px-4 py-1.5 text-xs font-medium uppercase tracking-wider text-blue-200 backdrop-blur-sm">
            Climate Crisis in Central Asia
          </span>
        </div>

        <h1 className="mb-6 text-5xl font-bold leading-tight tracking-tight text-white md:text-7xl">
          <span className="animate-fadeInUp inline-block" style={{ animationDelay: "0.3s" }}>
            Қазақстанның
          </span>{" "}
          <br />
          <span className="animate-fadeInUp inline-block" style={{ animationDelay: "0.6s" }}>
            <span className="bg-gradient-to-r from-blue-300 to-cyan-200 bg-clip-text text-transparent">
              мұздықтары
            </span>{" "}
            ериді
          </span>
        </h1>

        <p className="animate-fadeInUp mb-2 text-lg text-blue-200/80 md:text-xl" style={{ animationDelay: "0.9s" }}>
          Kazakhstan&apos;s glaciers are disappearing at an alarming rate
        </p>

        {/* Animated facts */}
        <div className="animate-fadeInUp mt-8 h-16" style={{ animationDelay: "1.2s" }}>
          {showStat && (
            <p key={factIndex} className="animate-fadeIn text-base text-blue-100/70 md:text-lg">
              {FACTS[factIndex]}
            </p>
          )}
        </div>

        {/* Dots indicator */}
        <div className="mt-4 flex items-center justify-center gap-2">
          {FACTS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-500 ${
                factIndex === i ? "w-6 bg-blue-300" : "w-1.5 bg-blue-500/40"
              }`}
            />
          ))}
        </div>

        {/* Scroll indicator */}
        <div className="animate-fadeInUp mt-12" style={{ animationDelay: "1.5s" }}>
          <ArrowDown className="mx-auto h-6 w-6 animate-bounce text-blue-300/60" />
        </div>
      </div>
    </section>
  );
}
